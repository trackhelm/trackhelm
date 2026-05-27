from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from typing import Dict

from pydantic import BaseModel
from pydantic import Field
from pydantic import PrivateAttr
import tomli


logger = logging.getLogger(__name__)


class ServerConfig(BaseModel):
    """Server connection configuration."""

    host: str
    port: int
    login: str
    password: str


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    dir: str = "logs"
    max_bytes: int = 5 * 1024 * 1024
    backup_count: int = 3


class PluginsConfig(BaseModel):
    """Plugins section configuration."""

    enabled: list[str] = Field(default_factory=list)


class TrackHelmConfig(BaseModel):
    """Top-level application configuration.

    This mirrors the requirements used by the controller and plugin
    discovery logic. Plugin-specific raw configs are stored in the
    private attribute ``_plugin_configs``.
    """

    server: ServerConfig
    database: DatabaseConfig
    logging: LoggingConfig = LoggingConfig()
    plugins: PluginsConfig

    # Stores raw plugin config dicts keyed by plugin name.
    _plugin_configs: Dict[str, Dict[str, Any]] = PrivateAttr(default_factory=dict)

    def plugin_config(self, key: str) -> Dict[str, Any]:
        """Return the raw dict for a plugin config or an empty dict."""

        return dict(self._plugin_configs.get(key, {}))

    @classmethod
    def from_file(
        cls, path: Path = Path("trackhelm.toml"), plugins_dir: Path = Path("plugins")
    ) -> "TrackHelmConfig":
        """Load configuration from a TOML file and discover plugin files.

        The method looks for an inline [plugins.<key>] block and for
        plugins/<key>.toml files. File-based configs take precedence.
        """

        with path.open("rb") as fh:
            raw = tomli.load(fh)

        server_data = raw.get("server", {})
        database_data = raw.get("database", {})
        logging_data = raw.get("logging", {})
        plugins_data = raw.get("plugins", {})

        cfg = cls(
            server=ServerConfig(**server_data),
            database=DatabaseConfig(**database_data),
            logging=LoggingConfig(**logging_data),
            plugins=PluginsConfig(**(plugins_data if isinstance(plugins_data, dict) else {})),
        )

        enabled = cfg.plugins.enabled

        # Discover plugin configs: file wins, otherwise inline, otherwise {}
        for key in enabled:
            file_path = plugins_dir / f"{key}.toml"
            if file_path.exists():
                try:
                    with file_path.open("rb") as fh:
                        cfg._plugin_configs[key] = tomli.load(fh)
                except Exception:
                    logger.exception("Failed to load plugin config from %s", file_path)
                    cfg._plugin_configs[key] = {}
            else:
                inline = plugins_data.get(key) if isinstance(plugins_data, dict) else None
                if isinstance(inline, dict):
                    cfg._plugin_configs[key] = dict(inline)
                else:
                    cfg._plugin_configs[key] = {}

        return cfg
