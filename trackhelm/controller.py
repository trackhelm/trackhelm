from __future__ import annotations

import asyncio
from collections.abc import Iterable
import logging
from pathlib import Path
from typing import Any

from .chat import ChatCommandRegistration
from .chat import ChatRouter
from .chat import ChatRouterHandler
from .config import TrackHelmConfig
from .database import DatabaseManager
from .eventbus.bus import EventBus
from .eventbus.events import ControllerTick
from .gbx.client import GbxClient
from .gbx.exceptions import AuthenticationError
from .logging import setup_logging
from .plugin.base import Plugin
from .plugin.loader import load_enabled_plugins
from .plugin.registry import PluginRegistry


logger = logging.getLogger(__name__)


class Controller:
    """Application controller coordinating core services and plugins."""

    def __init__(self, config: TrackHelmConfig) -> None:
        self.config: TrackHelmConfig = config
        self.bus: EventBus = EventBus()
        self.db: DatabaseManager = DatabaseManager(config.database.url)
        self.gbx: GbxClient = GbxClient(config.server, event_bus=self.bus)
        self.chat: ChatRouter = ChatRouter(self.bus, self.gbx.chat_forward_to_login)
        self.gbx.chat_router = self.chat.route_player_chat

        # Backwards-compatible alias used by older code.
        self.event_bus = self.bus

        self._registry = PluginRegistry()
        self._gbx_task: asyncio.Task[None] | None = None
        self._tick_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start core services and schedule GBX supervision."""

        await self.bus.start()
        await self._connect_gbx_for_startup()
        plugins = await load_enabled_plugins(self)
        await self.db.initialize()

        for plugin in plugins:
            await plugin.setup()
            self._registry.register(plugin)

        self._gbx_task = asyncio.create_task(
            self._gbx_supervision_loop(),
            name="gbx-supervisor",
        )
        self._tick_task = asyncio.create_task(self._tick_loop(), name="controller-tick")
        logger.info("Controller started with %s plugin(s)", len(plugins))

    async def stop(self) -> None:
        """Tear down plugins and core services."""

        try:
            await self._stop_tick_loop()
            await self._stop_gbx_supervision()

            for plugin in reversed(self._registry.all()):
                await plugin.teardown()
        finally:
            await self.gbx.disconnect()
            await self.bus.shutdown()
            await self.db.dispose()
            logger.info("Controller stopped")

    async def _connect_gbx_for_startup(self) -> None:
        reconnect = self.config.reconnect
        delay = reconnect.initial_delay_seconds

        while True:
            try:
                await self.gbx.connect()
                return
            except AuthenticationError:
                raise
            except asyncio.CancelledError:
                raise
            except Exception:
                if not reconnect.enabled:
                    raise

                logger.exception(
                    "Initial GBX connection failed; retrying in %.1f second(s)",
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * reconnect.multiplier, reconnect.max_delay_seconds)

    async def _gbx_supervision_loop(self) -> None:
        reconnect = self.config.reconnect
        delay = reconnect.initial_delay_seconds

        while True:
            try:
                await self.gbx.listen(self.bus)
                raise ConnectionError("GBX listener ended")
            except asyncio.CancelledError:
                raise
            except AuthenticationError:
                logger.exception("GBX authentication failed; reconnect supervision stopped")
                raise
            except Exception:
                logger.exception("GBX session ended unexpectedly")
                await self.gbx.disconnect()

                if not reconnect.enabled:
                    logger.error("GBX reconnect is disabled; supervision stopped")
                    return

                logger.info("Reconnecting to GBX in %.1f second(s)", delay)
                await asyncio.sleep(delay)

                try:
                    await self.gbx.connect()
                except AuthenticationError:
                    logger.exception("GBX authentication failed; reconnect supervision stopped")
                    raise
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("GBX reconnect attempt failed")
                    delay = min(delay * reconnect.multiplier, reconnect.max_delay_seconds)
                    continue

                delay = reconnect.initial_delay_seconds

    async def _stop_gbx_supervision(self) -> None:
        if self._gbx_task is None:
            return

        self._gbx_task.cancel()
        try:
            await self._gbx_task
        except asyncio.CancelledError:
            pass
        self._gbx_task = None

    async def _tick_loop(self) -> None:
        loop = asyncio.get_running_loop()
        next_tick = loop.time() + 1.0

        try:
            while True:
                await asyncio.sleep(max(0.0, next_tick - loop.time()))
                await self.bus.emit(ControllerTick())

                now = loop.time()
                next_tick += 1.0
                if next_tick <= now:
                    next_tick = now + 1.0
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Controller tick loop failed")

    async def _stop_tick_loop(self) -> None:
        if self._tick_task is None:
            return

        self._tick_task.cancel()
        try:
            await self._tick_task
        except asyncio.CancelledError:
            pass
        self._tick_task = None

    def plugin(self, name: str) -> Plugin[Any] | None:
        return self._registry.get(name)

    def register_chat_command(
        self,
        plugin_name: str,
        name: str,
        *,
        description: str = "",
        usage: str | None = None,
        aliases: Iterable[str] = (),
    ) -> ChatCommandRegistration:
        return self.chat.register_command(
            plugin_name,
            name,
            description=description,
            usage=usage,
            aliases=aliases,
        )

    def chat_commands(self) -> list[ChatCommandRegistration]:
        return self.chat.commands()

    def register_chat_router(self, plugin_name: str, handler: ChatRouterHandler) -> None:
        self.chat.register_route_handler(plugin_name, handler)

    @classmethod
    def run(cls, config_path: str = "trackhelm.toml") -> None:
        config = TrackHelmConfig.from_file(Path(config_path))

        level_name = config.logging.level.upper()
        level = logging.getLevelNamesMapping().get(level_name, logging.INFO)

        setup_logging(
            Path(config.logging.dir),
            config.logging.max_bytes,
            config.logging.backup_count,
            level,
        )

        controller = cls(config)
        asyncio.run(controller._main())

    async def _main(self) -> None:
        try:
            await self.start()
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()
