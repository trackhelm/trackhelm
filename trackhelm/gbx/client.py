from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import suppress
import itertools
import logging
from typing import Any

from trackhelm.config import ServerConfig
from trackhelm.eventbus.bus import EventBus
from trackhelm.eventbus.events import lookup_event_class
from trackhelm.eventbus.events import PlayerChat

from .codec import XmlRpcCodec
from .exceptions import AuthenticationError
from .exceptions import ConnectionClosed
from .exceptions import ProtocolError
from .exceptions import RequestTimeout
from .methods import GbxMethodsMixin
from .protocol import GBX_HEADER
from .protocol import Protocol


logger = logging.getLogger(__name__)


class GbxClient(GbxMethodsMixin):
    """
    Production-ready async TMNF GBXRemote client.

    Features:
    - asyncio-native
    - request/response futures
    - callback event dispatch
    - bounded concurrency
    - reconnect-ready architecture
    - multicall support
    - timeout enforcement
    - graceful shutdown
    """

    def __init__(
        self,
        host: str | ServerConfig,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        *,
        event_bus: EventBus,
        request_timeout: float = 10.0,
        max_payload_size: int = 16 * 1024 * 1024,
    ) -> None:
        if isinstance(host, ServerConfig):
            server = host
            host = server.host
            port = server.port
            username = server.login
            password = server.password

        if port is None or username is None or password is None:
            raise ValueError("port, username and password are required")

        self.host = host
        self.port = port

        self.username = username
        self.password = password

        self.request_timeout = request_timeout
        self.max_payload_size = max_payload_size

        self.event_bus = event_bus
        self.chat_router: Callable[[PlayerChat], Awaitable[None]] | None = None

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

        self._listener_task: asyncio.Task[None] | None = None
        self._callback_tasks: set[asyncio.Task[None]] = set()

        self._request_id = itertools.count(1)
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._pending_lock = asyncio.Lock()

        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        logger.info("Connecting to %s:%s", self.host, self.port)

        await self.shutdown()

        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.host,
                self.port,
            )

            await self._perform_handshake()

            self._listener_task = asyncio.create_task(
                self._listen_loop(),
                name="gbx-listener",
            )

            auth_ok = await self.authenticate(self.username, self.password)

            if not auth_ok:
                raise AuthenticationError("Authentication failed")

            # Use the typed wrapper from GbxMethodsMixin instead of calling
            # the XML-RPC method directly.
            await self.enable_callbacks(True)

            if self.chat_router is not None:
                await self.chat_enable_manual_routing(True, False)

            self._connected = True

            logger.info("Connected to TMNF server")
        except Exception:
            await self.shutdown()
            raise

    async def listen(self, event_bus: EventBus | None = None) -> None:
        if event_bus is not None:
            self.event_bus = event_bus

        if self._listener_task is None:
            raise ConnectionClosed("Not connected")

        await self._listener_task

    async def disconnect(self) -> None:
        await self.shutdown()

    async def shutdown(self) -> None:
        self._connected = False

        if self._listener_task:
            self._listener_task.cancel()

            with suppress(asyncio.CancelledError, Exception):
                await self._listener_task

        for task in list(self._callback_tasks):
            task.cancel()

        if self._callback_tasks:
            await asyncio.gather(*self._callback_tasks, return_exceptions=True)
            self._callback_tasks.clear()

        for future in self._pending.values():
            if not future.done():
                future.set_exception(ConnectionClosed())

        self._pending.clear()

        if self._writer:
            self._writer.close()
            with suppress(OSError):
                await self._writer.wait_closed()

        self._reader = None
        self._writer = None
        self._listener_task = None

        logger.info("GBX client shutdown complete")

    async def call(
        self,
        method: str,
        params: list[Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        listener_running = self._listener_task is not None and not self._listener_task.done()
        if not self._writer or not (self._connected or listener_running):
            raise ConnectionClosed("Not connected")

        params = params or []

        request_id = next(self._request_id)

        payload = XmlRpcCodec.encode(method, params)
        # Create a handle compatible with GBX protocol v2: set MSB
        handle = request_id | 0x80000000
        packet = Protocol.pack(payload, handle=handle)

        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        async with self._pending_lock:
            # Store keyed by handle so responses can be matched directly
            self._pending[handle] = future

        try:
            self._writer.write(packet)
            await self._writer.drain()

            return await asyncio.wait_for(
                future,
                timeout=timeout or self.request_timeout,
            )

        except asyncio.TimeoutError as exc:
            raise RequestTimeout(method) from exc

        except (ConnectionError, OSError) as exc:
            self._connected = False
            raise ConnectionClosed("Connection lost") from exc

        finally:
            async with self._pending_lock:
                self._pending.pop(handle, None)

    async def _perform_handshake(self) -> None:
        """
        GBXRemote handshake format:

        uint32 header_length
        bytes  protocol_string ("GBXRemote 2")
        uint32 version

        TMNF sends the protocol string prefixed with its length.
        """

        if not self._reader:
            raise ConnectionClosed()

        raw_size = await self._reader.readexactly(4)
        size, _is_callback, _ = Protocol.unpack_header(raw_size)

        protocol = await self._reader.readexactly(size)

        if protocol != GBX_HEADER:
            raise ProtocolError(f"Invalid GBX protocol header: {protocol!r}")

    async def _listen_loop(self) -> None:
        logger.info("GBX listener started")

        try:
            while True:
                await self._read_packet()

        except asyncio.CancelledError:
            raise

        except (asyncio.IncompleteReadError, ConnectionError, OSError) as exc:
            logger.warning("GBX listener lost connection: %s", exc)
            self._connected = False
            raise ConnectionClosed("Connection lost") from exc

        except Exception:
            logger.exception("GBX listener crashed")
            self._connected = False
            raise

    async def _read_packet(self) -> None:
        if not self._reader:
            raise ConnectionClosed()

        # Read size + handle (protocol v2)
        header = await self._reader.readexactly(8)
        size, is_callback, recv_handle = Protocol.unpack_header(header)

        if size > self.max_payload_size:
            raise ProtocolError(f"Payload too large: {size} > {self.max_payload_size}")

        payload = await self._reader.readexactly(size)

        method, data = XmlRpcCodec.decode(payload)

        logger.debug(
            "Received packet size=%s is_callback=%s handle=%s method=%s",
            size,
            is_callback,
            hex(recv_handle) if recv_handle is not None else None,
            method,
        )

        if is_callback:
            if not method:
                raise ProtocolError("Callback without method name")

            # Try to map the GBX callback to a typed Event class
            event_cls = lookup_event_class(method)
            if event_cls is not None:
                try:
                    event_instance = event_cls.from_gbx_params(data)
                except Exception:
                    logger.exception("Failed to construct typed event for %s", method)
                else:
                    if isinstance(event_instance, PlayerChat) and self.chat_router is not None:
                        self._schedule_chat_route(event_instance, method)
                        return
                    await self.event_bus.emit(event_instance)
                    return

            # Fallback to legacy payload emission
            await self.event_bus.emit(method, params=data)
            return

        # Match response to pending future by handle
        pending: asyncio.Future[Any] | None = None
        if recv_handle is not None:
            async with self._pending_lock:
                pending = self._pending.pop(recv_handle, None)

        if pending and not pending.done():
            pending.set_result(data)

    def _schedule_chat_route(self, event: PlayerChat, method: str) -> None:
        task = asyncio.create_task(
            self._route_chat_callback(event, method),
            name=f"gbx-chat-route-{event.login}",
        )
        self._callback_tasks.add(task)
        task.add_done_callback(self._callback_tasks.discard)

    async def _route_chat_callback(self, event: PlayerChat, method: str) -> None:
        if self.chat_router is None:
            return

        try:
            await self.chat_router(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to route manual chat for %s", method)
