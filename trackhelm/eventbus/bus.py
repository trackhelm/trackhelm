from __future__ import annotations

import asyncio
from collections import defaultdict
import inspect
import logging
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import cast
from typing import overload
from typing import Type
from typing import TypeVar
from typing import Union

from .events import BaseEvent
from .events import Event


logger = logging.getLogger(__name__)


E = TypeVar("E", bound=BaseEvent)

# Handler used for legacy `Event` or generic BaseEvent handlers at runtime.
Handler = Callable[[Union[Event, BaseEvent]], Awaitable[None] | None]


class EventBus:
    """
    Production-ready asyncio event bus with typed event support.
    """

    def __init__(
        self,
        *,
        queue_size: int = 1000,
        workers: int = 4,
        handler_timeout: float = 10.0,
    ) -> None:
        # queue stores either legacy `Event` or typed `BaseEvent` instances
        self._queue: asyncio.Queue[Union[Event, BaseEvent]] = asyncio.Queue(maxsize=queue_size)

        # handlers by GBX name (string) and by Event type
        self._handlers_by_name: dict[str, list[Handler]] = defaultdict(list)
        self._handlers_by_type: dict[Type[BaseEvent], list[Handler]] = defaultdict(list)

        self._workers = workers
        self._handler_timeout = handler_timeout

        self._tasks: list[asyncio.Task[None]] = []
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def queue_max_size(self) -> int:
        return self._queue.maxsize

    @property
    def worker_count(self) -> int:
        return len(self._tasks)

    @overload
    def subscribe(
        self, event: str, handler: Callable[[Event], Awaitable[None] | None]
    ) -> None:  # pragma: no cover - typing only
        ...

    @overload
    def subscribe(
        self, event: Type[E], handler: Callable[[E], Awaitable[None] | None]
    ) -> None:  # pragma: no cover - typing only
        ...

    def subscribe(
        self, event: Union[str, Type[E]], handler: Callable[..., Awaitable[None] | None]
    ) -> None:
        """Subscribe a handler to either a GBX callback name (str) or an Event class.

        Examples:
        - `subscribe("TrackMania.PlayerConnect", handler)`
        - `subscribe(PlayerConnect, handler)`
        """
        if isinstance(event, str):
            self._handlers_by_name[event].append(cast(Handler, handler))
        else:
            self._handlers_by_type[event].append(cast(Handler, handler))

    @overload
    def unsubscribe(
        self, event: str, handler: Callable[[Event], Awaitable[None] | None]
    ) -> None:  # pragma: no cover - typing only
        ...

    @overload
    def unsubscribe(
        self, event: Type[E], handler: Callable[[E], Awaitable[None] | None]
    ) -> None:  # pragma: no cover - typing only
        ...

    def unsubscribe(
        self, event: Union[str, Type[E]], handler: Callable[..., Awaitable[None] | None]
    ) -> None:
        if isinstance(event, str):
            if handler in self._handlers_by_name[event]:
                self._handlers_by_name[event].remove(handler)
        else:
            if handler in self._handlers_by_type[event]:
                self._handlers_by_type[event].remove(handler)

    async def emit(self, event_or_name: Union[str, BaseEvent], **payload: Any) -> None:
        """Emit either a legacy string-named event or a typed `BaseEvent` instance.

        - `emit("TrackMania.PlayerConnect", params=[...])` (legacy)
        - `emit(event_instance)` (typed)
        """
        if isinstance(event_or_name, BaseEvent):
            await self._queue.put(event_or_name)
            return

        # legacy path: create Event wrapper
        event = Event(name=event_or_name, payload=payload)
        await self._queue.put(event)

    async def start(self) -> None:
        if self._running:
            return

        self._running = True

        for idx in range(self._workers):
            task = asyncio.create_task(
                self._worker_loop(idx),
                name=f"eventbus-worker-{idx}",
            )
            self._tasks.append(task)

        logger.info("Event bus started with %s workers", self._workers)

    async def shutdown(self) -> None:
        self._running = False

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()

        logger.info("Event bus shutdown complete")

    async def _worker_loop(self, worker_id: int) -> None:
        logger.debug("Event worker %s started", worker_id)

        while self._running:
            try:
                event = await self._queue.get()
                await self._dispatch(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unhandled error in event worker")

    async def _dispatch(self, event: Union[Event, BaseEvent]) -> None:
        # Dispatch for typed and legacy events
        if isinstance(event, BaseEvent):
            # handlers registered for the event type
            handlers = list(self._handlers_by_type.get(type(event), []))
            # handlers registered by GBX name
            handlers += list(self._handlers_by_name.get(getattr(event, "gbx_name", ""), []))
            event_name = getattr(event, "gbx_name", "")
        else:
            handlers = list(self._handlers_by_name.get(event.name, []))
            event_name = event.name

        if not handlers:
            return

        for handler in handlers:
            try:
                result = handler(event)

                if inspect.isawaitable(result):
                    await asyncio.wait_for(
                        result,
                        timeout=self._handler_timeout,
                    )

            except asyncio.TimeoutError:
                logger.warning(
                    "Handler timeout for event=%s handler=%s",
                    event_name,
                    getattr(handler, "__name__", repr(handler)),
                )
            except Exception:
                logger.exception(
                    "Handler failed for event=%s handler=%s",
                    event_name,
                    getattr(handler, "__name__", repr(handler)),
                )
