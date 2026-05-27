from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection


if TYPE_CHECKING:
    from trackhelm.controller import Controller


def _resolve_migrations_path(package: str) -> Path:
    """Resolve a migrations package to a filesystem path."""

    with resources.path(package, "__init__.py") as init_path:
        return init_path.parent


class PluginMigration:
    migration_package: str
    migration_version_table: str
    controller: Controller

    async def run_migrations(self) -> None:
        migrations_path = _resolve_migrations_path(self.migration_package)

        async with self.controller.db.engine.begin() as conn:
            await conn.run_sync(self._run_sync, migrations_path)

    def _run_sync(self, connection: Connection, migrations_path: Path) -> None:
        cfg = Config()
        cfg.set_main_option("script_location", str(migrations_path))
        cfg.set_main_option("version_table", self.migration_version_table)
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
