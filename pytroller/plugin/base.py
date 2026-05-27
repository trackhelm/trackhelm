from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Awaitable
from typing import Callable
from typing import ClassVar
from typing import Generic
from typing import TYPE_CHECKING
from typing import TypeVar

from pytroller.database.manager import DatabaseManager
from pytroller.eventbus.events import BaseEvent
from pytroller.gbx.client import GbxClient

from .config import PluginConfig


if TYPE_CHECKING:
    from pytroller.controller import Controller


ConfigT = TypeVar("ConfigT", bound=PluginConfig)
EventT = TypeVar("EventT", bound=BaseEvent)
AsyncHandler = Callable[[EventT], Awaitable[None] | None]


class Plugin(ABC, Generic[ConfigT]):
    """Base class for all pytroller plugins."""

    required_plugins: ClassVar[list[str]] = []
    optional_plugins: ClassVar[list[str]] = []
    config_class: ClassVar[type[PluginConfig]] = PluginConfig

    controller: Controller
    _config: ConfigT

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
        self.controller.bus.subscribe(event_type, handler)

    @property
    def db(self) -> DatabaseManager:
        return self.controller.db

    @property
    def gbx(self) -> GbxClient:
        return self.controller.gbx
