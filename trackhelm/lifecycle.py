from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ControllerState(StrEnum):
    """High-level controller lifecycle state."""

    STARTING = "starting"
    CONNECTED = "connected"
    PLUGINS_READY = "plugins_ready"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class PluginLifecycleStatus(StrEnum):
    """Startup/teardown status for a plugin instance."""

    DISCOVERED = "discovered"
    SETUP_STARTED = "setup_started"
    READY = "ready"
    FAILED = "failed"
    TEARDOWN_STARTED = "teardown_started"
    TORN_DOWN = "torn_down"


@dataclass(frozen=True, slots=True)
class CoreErrorRecord:
    """Bounded diagnostic record for recent core errors."""

    timestamp: datetime
    component: str
    stage: str
    message: str
    exception_type: str | None = None


@dataclass(frozen=True, slots=True)
class GbxHealth:
    connected: bool
    host: str
    port: int
    reconnect_supervision_active: bool


@dataclass(frozen=True, slots=True)
class EventBusHealth:
    running: bool
    queue_size: int
    queue_max_size: int
    worker_count: int


@dataclass(frozen=True, slots=True)
class PluginHealth:
    name: str
    status: PluginLifecycleStatus


@dataclass(frozen=True, slots=True)
class DatabaseHealth:
    reachable: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ControllerHealth:
    state: ControllerState
    ready: bool
    starting: bool
    stopping: bool
    degraded: bool
    gbx: GbxHealth
    event_bus: EventBusHealth
    plugins: tuple[PluginHealth, ...]
    database: DatabaseHealth
    recent_errors: tuple[CoreErrorRecord, ...]
