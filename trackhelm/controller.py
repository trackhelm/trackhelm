from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from .config import TrackHelmConfig
from .database import DatabaseManager
from .database import models as _database_models  # noqa: F401
from .eventbus.bus import EventBus
from .gbx.client import GbxClient
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

        # Backwards-compatible alias used by older code.
        self.event_bus = self.bus

        self._registry = PluginRegistry()
        self._listen_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start core services and schedule the GBX listen loop."""

        await self.gbx.connect()
        plugins = await load_enabled_plugins(self)
        await self.db.initialize()

        for plugin in plugins:
            await plugin.setup()
            self._registry.register(plugin)

        self._listen_task = asyncio.create_task(self.gbx.listen(self.bus), name="gbx-listen")
        logger.info("Controller started with %s plugin(s)", len(plugins))

    async def stop(self) -> None:
        """Tear down plugins and core services."""

        try:
            for plugin in reversed(self._registry.all()):
                await plugin.teardown()
        finally:
            if self._listen_task is not None:
                self._listen_task.cancel()
                try:
                    await self._listen_task
                except asyncio.CancelledError:
                    pass
                self._listen_task = None

            await self.gbx.disconnect()
            await self.bus.shutdown()
            await self.db.dispose()
            logger.info("Controller stopped")

    def plugin(self, name: str) -> Plugin[Any] | None:
        return self._registry.get(name)

    @classmethod
    def run(cls, config_path: str = "trackhelm.toml") -> None:
        config = TrackHelmConfig.from_file(Path(config_path))

        level_name = config.logging.level.upper()
        # Use getLevelNamesMapping() when available (Python 3.11+),
        # otherwise fall back to the internal mapping for older Pythons.
        if hasattr(logging, "getLevelNamesMapping"):
            level = logging.getLevelNamesMapping().get(level_name, logging.INFO)
        else:
            level = logging._nameToLevel.get(level_name, logging.INFO)

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
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await self.stop()
