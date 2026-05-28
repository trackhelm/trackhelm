from __future__ import annotations

from abc import ABC
from abc import abstractmethod
import asyncio
from collections.abc import Coroutine
from collections.abc import Iterable
from typing import Awaitable
from typing import Callable
from typing import ClassVar
from typing import Generic
from typing import TYPE_CHECKING
from typing import TypeVar

from trackhelm.chat import ChatCommandRegistration
from trackhelm.chat import ChatRouterHandler
from trackhelm.database.manager import DatabaseManager
from trackhelm.eventbus.events import BaseEvent
from trackhelm.gbx.client import GbxClient

from .config import PluginConfig


if TYPE_CHECKING:
    from trackhelm.controller import Controller


ConfigT = TypeVar("ConfigT", bound=PluginConfig)
EventT = TypeVar("EventT", bound=BaseEvent)
TaskResultT = TypeVar("TaskResultT")
AsyncHandler = Callable[[EventT], Awaitable[None] | None]
TrackedHandler = Callable[..., Awaitable[None] | None]


class Plugin(ABC, Generic[ConfigT]):
    """Base class for all TrackHelm plugins."""

    required_plugins: ClassVar[list[str]] = []
    optional_plugins: ClassVar[list[str]] = []
    config_class: ClassVar[type[PluginConfig]] = PluginConfig

    controller: Controller
    _config: ConfigT
    _subscriptions: list[tuple[type[BaseEvent], TrackedHandler]]

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the plugin entry-point key."""

    async def setup(self) -> None:
        """Perform plugin startup work."""

    async def teardown(self) -> None:
        """Perform plugin shutdown work."""

    @property
    def config(self) -> ConfigT:
        return self._config

    def subscribe(self, event_type: type[EventT], handler: AsyncHandler[EventT]) -> None:
        self.controller.bus.subscribe(event_type, handler, owner=self.name)
        self._ensure_tracking()
        self._subscriptions.append((event_type, handler))

    def register_chat_command(
        self,
        name: str,
        *,
        description: str = "",
        usage: str | None = None,
        aliases: Iterable[str] = (),
    ) -> ChatCommandRegistration:
        return self.controller.register_chat_command(
            self.name,
            name,
            description=description,
            usage=usage,
            aliases=aliases,
        )

    def register_chat_router(self, handler: ChatRouterHandler) -> None:
        self.controller.register_chat_router(self.name, handler)

    def create_task(
        self,
        coro: Coroutine[object, object, TaskResultT],
        *,
        name: str,
    ) -> asyncio.Task[TaskResultT]:
        return self.controller.create_task(coro, name=name, plugin_name=self.name)

    def cleanup_registered_side_effects(self) -> None:
        """Undo registrations made through the plugin helper API."""

        self._ensure_tracking()

        for event_type, handler in reversed(self._subscriptions):
            self.controller.bus.unsubscribe(event_type, handler)
        self._subscriptions.clear()

        self.controller.chat.unregister_plugin(self.name)

    def _ensure_tracking(self) -> None:
        if not hasattr(self, "_subscriptions"):
            self._subscriptions = []

    @property
    def db(self) -> DatabaseManager:
        return self.controller.db

    @property
    def gbx(self) -> GbxClient:
        return self.controller.gbx
