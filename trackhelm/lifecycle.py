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
    DISABLED = "disabled"
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
    plugin: str | None = None
    event: str | None = None
    task: str | None = None


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
    metrics: "EventBusMetrics"


@dataclass(frozen=True, slots=True)
class PluginHealth:
    name: str
    status: PluginLifecycleStatus
    enabled: bool = True
    fault_count: int = 0
    last_fault: str | None = None
    disabled_reason: str | None = None


@dataclass(frozen=True, slots=True)
class EventBusMetrics:
    emitted: int
    dispatched: int
    dropped: int
    failed: int
    timed_out: int
    slow: int


@dataclass(frozen=True, slots=True)
class TaskHealth:
    running: int
    crashed: int


@dataclass(frozen=True, slots=True)
class DatabaseHealth:
    reachable: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class CapabilityCheck:
    name: str
    ok: bool
    message: str = ""


@dataclass(frozen=True, slots=True)
class ReloadResult:
    applied: bool
    reloaded_plugins: tuple[str, ...] = ()
    enabled_plugins: tuple[str, ...] = ()
    disabled_plugins: tuple[str, ...] = ()
    pending_restart: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


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
    tasks: TaskHealth
    database: DatabaseHealth
    capabilities: tuple[CapabilityCheck, ...]
    recent_errors: tuple[CoreErrorRecord, ...]
