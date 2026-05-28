from __future__ import annotations

import logging
from pathlib import Path
import tomllib
from typing import Any
from typing import Dict

from pydantic import BaseModel
from pydantic import Field
from pydantic import PrivateAttr


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


class ReconnectConfig(BaseModel):
    """GBX reconnect supervision configuration."""

    enabled: bool = True
    initial_delay_seconds: float = Field(default=1.0, ge=0.0)
    max_delay_seconds: float = Field(default=30.0, ge=0.0)
    multiplier: float = Field(default=2.0, ge=1.0)
    max_retry_time_seconds: float = Field(default=300.0, ge=0.0)


class EventBusConfig(BaseModel):
    """Event dispatch and overload configuration."""

    queue_size: int = Field(default=1000, ge=1)
    workers: int = Field(default=4, ge=1)
    handler_timeout_seconds: float = Field(default=10.0, ge=0.1)
    slow_handler_warning_seconds: float = Field(default=1.0, ge=0.0)
    high_priority_timeout_seconds: float = Field(default=1.0, ge=0.0)
    overload_policy: str = "drop_newest"


class PluginFaultConfig(BaseModel):
    """Plugin fault isolation configuration."""

    max_failures: int = Field(default=3, ge=1)


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
    reconnect: ReconnectConfig = ReconnectConfig()
    event_bus: EventBusConfig = EventBusConfig()
    plugin_faults: PluginFaultConfig = PluginFaultConfig()
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
            raw = tomllib.load(fh)

        server_data = raw.get("server", {})
        database_data = raw.get("database", {})
        logging_data = raw.get("logging", {})
        reconnect_data = raw.get("reconnect", {})
        event_bus_data = raw.get("event_bus", {})
        plugin_faults_data = raw.get("plugin_faults", {})
        plugins_data = raw.get("plugins", {})

        cfg = cls(
            server=ServerConfig(**server_data),
            database=DatabaseConfig(**database_data),
            logging=LoggingConfig(**logging_data),
            reconnect=ReconnectConfig(
                **(reconnect_data if isinstance(reconnect_data, dict) else {})
            ),
            event_bus=EventBusConfig(
                **(event_bus_data if isinstance(event_bus_data, dict) else {})
            ),
            plugin_faults=PluginFaultConfig(
                **(plugin_faults_data if isinstance(plugin_faults_data, dict) else {})
            ),
            plugins=PluginsConfig(**(plugins_data if isinstance(plugins_data, dict) else {})),
        )

        enabled = cfg.plugins.enabled

        # Discover plugin configs: file wins, otherwise inline, otherwise {}
        for key in enabled:
            file_path = plugins_dir / f"{key}.toml"
            if file_path.exists():
                try:
                    with file_path.open("rb") as fh:
                        cfg._plugin_configs[key] = tomllib.load(fh)
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
