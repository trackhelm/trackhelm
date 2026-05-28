from __future__ import annotations

import asyncio
from collections.abc import Callable
from collections.abc import Coroutine
from dataclasses import dataclass
import logging
from typing import Any
from typing import TypeVar


logger = logging.getLogger(__name__)

TaskFaultHandler = Callable[[str | None, str, BaseException], Coroutine[Any, Any, None]]
TaskResultT = TypeVar("TaskResultT")


@dataclass(slots=True)
class _TaskRecord:
    task: asyncio.Task[Any]
    name: str
    owner: str | None


class TaskSupervisor:
    """Own background tasks and report crashes through one path."""

    def __init__(
        self,
        *,
        fault_handler: TaskFaultHandler | None = None,
        cancel_timeout: float = 5.0,
    ) -> None:
        self._fault_handler = fault_handler
        self._cancel_timeout = cancel_timeout
        self._tasks: dict[asyncio.Task[Any], _TaskRecord] = {}
        self._crashed = 0

    @property
    def running_count(self) -> int:
        return sum(1 for task in self._tasks if not task.done())

    @property
    def crashed_count(self) -> int:
        return self._crashed

    def create_task(
        self,
        coro: Coroutine[Any, Any, TaskResultT],
        *,
        name: str,
        owner: str | None = None,
    ) -> asyncio.Task[TaskResultT]:
        task: asyncio.Task[TaskResultT] = asyncio.create_task(coro, name=name)
        self._tasks[task] = _TaskRecord(task=task, name=name, owner=owner)
        task.add_done_callback(self._on_done)
        return task

    async def cancel_owner(self, owner: str) -> None:
        await self._cancel_records(
            [record for record in self._tasks.values() if record.owner == owner]
        )

    async def cancel_all(self) -> None:
        await self._cancel_records(list(self._tasks.values()))

    async def _cancel_records(self, records: list[_TaskRecord]) -> None:
        tasks = [record.task for record in records if not record.task.done()]
        for task in tasks:
            task.cancel()

        if not tasks:
            return

        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self._cancel_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Timed out while cancelling supervised tasks")

    def _on_done(self, task: asyncio.Task[Any]) -> None:
        record = self._tasks.pop(task, None)
        if record is None or task.cancelled():
            return

        exc = task.exception()
        if exc is None:
            return

        self._crashed += 1
        logger.error(
            "Supervised task crashed",
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={"task": record.name, "plugin": record.owner},
        )

        if self._fault_handler is not None:
            fault_task: asyncio.Task[None] = asyncio.create_task(
                self._fault_handler(record.owner, record.name, exc)
            )
            del fault_task
