from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable as AwaitableABC
from dataclasses import dataclass
import inspect
import logging
from time import perf_counter
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import cast
from typing import overload
from typing import Type
from typing import TypeVar
from typing import Union

from trackhelm.lifecycle import EventBusMetrics

from .events import BaseEvent
from .events import ControllerStateChanged
from .events import Event


logger = logging.getLogger(__name__)


E = TypeVar("E", bound=BaseEvent)

# Handler used for legacy `Event` or generic BaseEvent handlers at runtime.
Handler = Callable[[Union[Event, BaseEvent]], Awaitable[None] | None]
FaultHandler = Callable[[str, str, str, BaseException | None], AwaitableABC[None]]


@dataclass(slots=True)
class _HandlerRegistration:
    handler: Handler
    owner: str | None = None


@dataclass(slots=True)
class _MutableEventBusMetrics:
    emitted: int = 0
    dispatched: int = 0
    dropped: int = 0
    failed: int = 0
    timed_out: int = 0
    slow: int = 0


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
        slow_handler_warning: float = 1.0,
        high_priority_timeout: float = 1.0,
        overload_policy: str = "drop_newest",
        fault_handler: FaultHandler | None = None,
    ) -> None:
        # queue stores either legacy `Event` or typed `BaseEvent` instances
        self._queue: asyncio.Queue[Union[Event, BaseEvent]] = asyncio.Queue(maxsize=queue_size)

        # handlers by GBX name (string) and by Event type
        self._handlers_by_name: dict[str, list[_HandlerRegistration]] = defaultdict(list)
        self._handlers_by_type: dict[Type[BaseEvent], list[_HandlerRegistration]] = defaultdict(
            list
        )

        self._workers = workers
        self._handler_timeout = handler_timeout
        self._slow_handler_warning = slow_handler_warning
        self._high_priority_timeout = high_priority_timeout
        self._overload_policy = overload_policy
        self._fault_handler = fault_handler
        self._metrics = _MutableEventBusMetrics()

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

    @property
    def metrics(self) -> EventBusMetrics:
        return EventBusMetrics(
            emitted=self._metrics.emitted,
            dispatched=self._metrics.dispatched,
            dropped=self._metrics.dropped,
            failed=self._metrics.failed,
            timed_out=self._metrics.timed_out,
            slow=self._metrics.slow,
        )

    def configure(
        self,
        *,
        handler_timeout: float | None = None,
        slow_handler_warning: float | None = None,
        high_priority_timeout: float | None = None,
        overload_policy: str | None = None,
    ) -> None:
        if handler_timeout is not None:
            self._handler_timeout = handler_timeout
        if slow_handler_warning is not None:
            self._slow_handler_warning = slow_handler_warning
        if high_priority_timeout is not None:
            self._high_priority_timeout = high_priority_timeout
        if overload_policy is not None:
            self._overload_policy = overload_policy

    @overload
    def subscribe(
        self,
        event: str,
        handler: Callable[[Event], Awaitable[None] | None],
        *,
        owner: str | None = None,
    ) -> None:  # pragma: no cover - typing only
        ...

    @overload
    def subscribe(
        self,
        event: Type[E],
        handler: Callable[[E], Awaitable[None] | None],
        *,
        owner: str | None = None,
    ) -> None:  # pragma: no cover - typing only
        ...

    def subscribe(
        self,
        event: Union[str, Type[E]],
        handler: Callable[..., Awaitable[None] | None],
        *,
        owner: str | None = None,
    ) -> None:
        """Subscribe a handler to either a GBX callback name (str) or an Event class.

        Examples:
        - `subscribe("TrackMania.PlayerConnect", handler)`
        - `subscribe(PlayerConnect, handler)`
        """
        registration = _HandlerRegistration(cast(Handler, handler), owner)
        if isinstance(event, str):
            self._handlers_by_name[event].append(registration)
        else:
            self._handlers_by_type[event].append(registration)

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
        def remove(registrations: list[_HandlerRegistration]) -> None:
            registrations[:] = [
                registration for registration in registrations if registration.handler != handler
            ]

        if isinstance(event, str):
            remove(self._handlers_by_name[event])
        else:
            remove(self._handlers_by_type[event])

    async def emit(self, event_or_name: Union[str, BaseEvent], **payload: Any) -> None:
        """Emit either a legacy string-named event or a typed `BaseEvent` instance.

        - `emit("TrackMania.PlayerConnect", params=[...])` (legacy)
        - `emit(event_instance)` (typed)
        """
        self._metrics.emitted += 1
        if isinstance(event_or_name, BaseEvent):
            await self._enqueue(event_or_name)
            return

        # legacy path: create Event wrapper
        event = Event(name=event_or_name, payload=payload)
        await self._enqueue(event)

    async def _enqueue(self, event: Union[Event, BaseEvent]) -> None:
        if self._is_high_priority(event):
            try:
                await asyncio.wait_for(
                    self._queue.put(event),
                    timeout=self._high_priority_timeout,
                )
            except asyncio.TimeoutError:
                self._drop_event(event)
            return

        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._drop_event(event)

    def _drop_event(self, event: Union[Event, BaseEvent]) -> None:
        self._metrics.dropped += 1
        logger.warning(
            "Dropped event because event bus queue is full",
            extra={"event": self._event_name(event), "overload_policy": self._overload_policy},
        )

    def _is_high_priority(self, event: Union[Event, BaseEvent]) -> bool:
        return isinstance(event, ControllerStateChanged)

    def _event_name(self, event: Union[Event, BaseEvent]) -> str:
        if isinstance(event, BaseEvent):
            return getattr(event, "gbx_name", type(event).__name__)
        return event.name

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

        for registration in handlers:
            try:
                handler = registration.handler
                started_at = perf_counter()
                result = handler(event)

                if inspect.isawaitable(result):
                    await asyncio.wait_for(
                        result,
                        timeout=self._handler_timeout,
                    )
                elapsed = perf_counter() - started_at
                self._metrics.dispatched += 1
                if elapsed >= self._slow_handler_warning:
                    self._metrics.slow += 1
                    logger.warning(
                        "Slow handler for event=%s handler=%s elapsed=%.3fs",
                        event_name,
                        getattr(handler, "__name__", repr(handler)),
                        elapsed,
                    )

            except asyncio.TimeoutError:
                self._metrics.timed_out += 1
                logger.warning(
                    "Handler timeout for event=%s handler=%s",
                    event_name,
                    getattr(registration.handler, "__name__", repr(registration.handler)),
                )
                await self._report_fault(registration, event_name, TimeoutError())
            except Exception as exc:
                self._metrics.failed += 1
                logger.exception(
                    "Handler failed for event=%s handler=%s",
                    event_name,
                    getattr(registration.handler, "__name__", repr(registration.handler)),
                )
                await self._report_fault(registration, event_name, exc)

    async def _report_fault(
        self,
        registration: _HandlerRegistration,
        event_name: str,
        exc: BaseException | None,
    ) -> None:
        if registration.owner is None or self._fault_handler is None:
            return

        await self._fault_handler(
            registration.owner,
            event_name,
            getattr(registration.handler, "__name__", repr(registration.handler)),
            exc,
        )
