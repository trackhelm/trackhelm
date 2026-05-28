from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Iterable
from datetime import datetime
from datetime import UTC
import logging
from pathlib import Path
from typing import Any

from .chat import ChatCommandRegistration
from .chat import ChatRouter
from .chat import ChatRouterHandler
from .config import TrackHelmConfig
from .database import DatabaseManager
from .eventbus.bus import EventBus
from .eventbus.events import ControllerStateChanged
from .eventbus.events import ControllerTick
from .gbx.client import GbxClient
from .gbx.exceptions import AuthenticationError
from .gbx.exceptions import ConnectionClosed
from .lifecycle import CapabilityCheck
from .lifecycle import ControllerHealth
from .lifecycle import ControllerState
from .lifecycle import CoreErrorRecord
from .lifecycle import DatabaseHealth
from .lifecycle import EventBusHealth
from .lifecycle import GbxHealth
from .lifecycle import PluginHealth
from .lifecycle import PluginLifecycleStatus
from .lifecycle import ReloadResult
from .lifecycle import TaskHealth
from .logging import setup_logging
from .plugin.base import Plugin
from .plugin.loader import load_enabled_plugins
from .plugin.registry import PluginRegistry
from .tasks import TaskSupervisor


logger = logging.getLogger(__name__)


class _ReconnectTimeoutError(Exception):
    """Raised when GBX reconnect attempts exceed the configured time budget."""


class Controller:
    """Application controller coordinating core services and plugins."""

    _RECENT_ERROR_LIMIT = 20

    def __init__(self, config: TrackHelmConfig) -> None:
        self.config: TrackHelmConfig = config
        self.bus: EventBus = EventBus(
            queue_size=config.event_bus.queue_size,
            workers=config.event_bus.workers,
            handler_timeout=config.event_bus.handler_timeout_seconds,
            slow_handler_warning=config.event_bus.slow_handler_warning_seconds,
            high_priority_timeout=config.event_bus.high_priority_timeout_seconds,
            overload_policy=config.event_bus.overload_policy,
            fault_handler=self._handle_plugin_handler_fault,
        )
        self.db: DatabaseManager = DatabaseManager(config.database.url)
        self.gbx: GbxClient = GbxClient(config.server, event_bus=self.bus)
        self.chat: ChatRouter = ChatRouter(self.bus, self.gbx.chat_forward_to_login)
        self.gbx.chat_router = self.chat.route_player_chat

        # Backwards-compatible alias used by older code.
        self.event_bus = self.bus

        self._registry = PluginRegistry()
        self._gbx_task: asyncio.Task[None] | None = None
        self._tick_task: asyncio.Task[None] | None = None
        self._shutdown_event: asyncio.Event | None = None
        self._state = ControllerState.STOPPED
        self._recent_errors: deque[CoreErrorRecord] = deque(maxlen=self._RECENT_ERROR_LIMIT)
        self._plugin_statuses: dict[str, PluginLifecycleStatus] = {}
        self._known_plugins: dict[str, Plugin[Any]] = {}
        self._plugin_fault_counts: dict[str, int] = {}
        self._plugin_last_faults: dict[str, str] = {}
        self._plugin_disabled_reasons: dict[str, str] = {}
        self._capability_checks: list[CapabilityCheck] = []
        self.tasks = TaskSupervisor(fault_handler=self._handle_task_fault)

    async def start(self) -> None:
        """Start core services and schedule GBX supervision."""

        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()

        await self._set_state(ControllerState.STARTING, "controller starting")
        await self.bus.start()
        try:
            await self._connect_gbx_for_startup()
            await self._check_capabilities()
            await self._set_state(ControllerState.CONNECTED, "GBX session connected")
            plugins = await load_enabled_plugins(self)
            self._track_discovered_plugins(plugins)
            await self.db.initialize()

            await self._setup_plugins(plugins)

            self._gbx_task = self.create_task(
                self._gbx_supervision_loop(),
                name="gbx-supervisor",
            )
            self._tick_task = self.create_task(self._tick_loop(), name="controller-tick")
            await self._set_state(ControllerState.PLUGINS_READY, "plugins ready")
            logger.info("Controller started with %s plugin(s)", len(plugins))
        except Exception as exc:
            self._record_error("controller", "startup", "Controller startup failed", exc)
            await self._set_state(ControllerState.FAILED, "startup failed")
            await self._rollback_plugin_setup()
            raise

    async def stop(self) -> None:
        """Tear down plugins and core services."""

        try:
            await self._set_state(ControllerState.STOPPING, "controller stopping")
            await self._stop_tick_loop()
            await self._stop_gbx_supervision()
            await self.tasks.cancel_all()

            for plugin in reversed(self._registry.all()):
                await self._teardown_plugin(plugin)
        finally:
            await self.gbx.disconnect()
            await self.db.dispose()
            await self._set_state(ControllerState.STOPPED, "controller stopped")
            await self.bus.shutdown()
            logger.info("Controller stopped")

    @property
    def state(self) -> ControllerState:
        return self._state

    @property
    def ready(self) -> bool:
        return self._state is ControllerState.PLUGINS_READY

    async def health(self) -> ControllerHealth:
        db_error: str | None = None
        try:
            await self.db.check_reachable()
        except Exception as exc:
            db_error = str(exc)

        return ControllerHealth(
            state=self._state,
            ready=self.ready,
            starting=self._state is ControllerState.STARTING,
            stopping=self._state is ControllerState.STOPPING,
            degraded=self._state is ControllerState.DEGRADED,
            gbx=GbxHealth(
                connected=self.gbx.connected,
                host=self.gbx.host,
                port=self.gbx.port,
                reconnect_supervision_active=self._gbx_task is not None
                and not self._gbx_task.done(),
            ),
            event_bus=EventBusHealth(
                running=self.bus.running,
                queue_size=self.bus.queue_size,
                queue_max_size=self.bus.queue_max_size,
                worker_count=self.bus.worker_count,
                metrics=self.bus.metrics,
            ),
            plugins=tuple(
                PluginHealth(
                    name=name,
                    status=status,
                    enabled=status is not PluginLifecycleStatus.DISABLED,
                    fault_count=self._plugin_fault_counts.get(name, 0),
                    last_fault=self._plugin_last_faults.get(name),
                    disabled_reason=self._plugin_disabled_reasons.get(name),
                )
                for name, status in self._plugin_statuses.items()
            ),
            tasks=TaskHealth(
                running=self.tasks.running_count,
                crashed=self.tasks.crashed_count,
            ),
            database=DatabaseHealth(reachable=db_error is None, error=db_error),
            capabilities=tuple(self._capability_checks),
            recent_errors=tuple(self._recent_errors),
        )

    def create_task(
        self,
        coro: Any,
        *,
        name: str,
        plugin_name: str | None = None,
    ) -> asyncio.Task[Any]:
        return self.tasks.create_task(coro, name=name, owner=plugin_name)

    async def reload_config(self, path: Path | None = None) -> ReloadResult:
        config_path = path or Path("trackhelm.toml")
        old_config = self.config
        try:
            new_config = TrackHelmConfig.from_file(config_path)
            self.config = new_config
            resolved_plugins = await load_enabled_plugins(self)
        except Exception as exc:
            self.config = old_config
            self._record_error("config", "reload", "Config reload rejected", exc)
            logger.exception("Config reload rejected")
            return ReloadResult(applied=False, errors=(str(exc),))

        self._apply_reloadable_core_config(new_config)

        pending_restart = self._pending_restart_changes(old_config, new_config)
        current_plugins = set(self._registry._plugins)
        resolved_plugin_names = {plugin.name for plugin in resolved_plugins}
        disabled: list[str] = []
        enabled: list[str] = []

        for plugin_name in sorted(current_plugins - resolved_plugin_names):
            await self._disable_plugin(plugin_name, "disabled by config reload")
            disabled.append(plugin_name)

        if any(plugin.name not in current_plugins for plugin in resolved_plugins):
            await self.db.initialize()

        for plugin in resolved_plugins:
            plugin_name = plugin.name
            if plugin_name in current_plugins:
                continue
            self._track_discovered_plugins([plugin])
            await self._setup_plugins([plugin])
            enabled.append(plugin_name)

        logger.info(
            "Config reload applied",
            extra={"enabled_plugins": enabled, "disabled_plugins": disabled},
        )
        return ReloadResult(
            applied=True,
            enabled_plugins=tuple(enabled),
            disabled_plugins=tuple(disabled),
            pending_restart=tuple(pending_restart),
        )

    def _apply_reloadable_core_config(self, config: TrackHelmConfig) -> None:
        level_name = config.logging.level.upper()
        level = logging.getLevelNamesMapping().get(level_name, logging.INFO)
        logging.getLogger().setLevel(level)
        for handler in logging.getLogger().handlers:
            handler.setLevel(level)

        self.bus.configure(
            handler_timeout=config.event_bus.handler_timeout_seconds,
            slow_handler_warning=config.event_bus.slow_handler_warning_seconds,
            high_priority_timeout=config.event_bus.high_priority_timeout_seconds,
            overload_policy=config.event_bus.overload_policy,
        )

    def _pending_restart_changes(
        self,
        old: TrackHelmConfig,
        new: TrackHelmConfig,
    ) -> list[str]:
        pending: list[str] = []
        if old.server != new.server:
            pending.append("server")
        if old.database != new.database:
            pending.append("database")
        if (
            old.logging.dir,
            old.logging.max_bytes,
            old.logging.backup_count,
        ) != (
            new.logging.dir,
            new.logging.max_bytes,
            new.logging.backup_count,
        ):
            pending.append("logging.rotation")
        if (
            old.event_bus.queue_size,
            old.event_bus.workers,
        ) != (
            new.event_bus.queue_size,
            new.event_bus.workers,
        ):
            pending.append("event_bus.capacity")
        return pending

    async def _set_state(self, state: ControllerState, reason: str) -> None:
        previous = self._state
        if previous is state:
            return

        self._state = state
        logger.info("Controller state changed: %s -> %s (%s)", previous, state, reason)
        await self.bus.emit(
            ControllerStateChanged(
                previous=previous,
                current=state,
                reason=reason,
            )
        )

    def _record_error(
        self,
        component: str,
        stage: str,
        message: str,
        exc: BaseException | None = None,
        *,
        plugin: str | None = None,
        event: str | None = None,
        task: str | None = None,
    ) -> None:
        self._recent_errors.append(
            CoreErrorRecord(
                timestamp=datetime.now(UTC),
                component=component,
                stage=stage,
                message=message,
                exception_type=type(exc).__name__ if exc is not None else None,
                plugin=plugin,
                event=event,
                task=task,
            )
        )

    async def _handle_plugin_handler_fault(
        self,
        plugin_name: str,
        event_name: str,
        handler_name: str,
        exc: BaseException | None,
    ) -> None:
        await self._register_plugin_fault(
            plugin_name,
            f"handler {handler_name} failed for {event_name}",
            exc,
            event=event_name,
        )

    async def _handle_task_fault(
        self,
        plugin_name: str | None,
        task_name: str,
        exc: BaseException,
    ) -> None:
        if plugin_name is None:
            self._record_error(
                "task",
                "core",
                f"Core task '{task_name}' crashed",
                exc,
                task=task_name,
            )
            await self._set_state(ControllerState.FAILED, f"core task {task_name} crashed")
            self._request_shutdown()
            return

        await self._register_plugin_fault(
            plugin_name,
            f"task {task_name} crashed",
            exc,
            task=task_name,
        )

    async def _register_plugin_fault(
        self,
        plugin_name: str,
        message: str,
        exc: BaseException | None,
        *,
        event: str | None = None,
        task: str | None = None,
    ) -> None:
        count = self._plugin_fault_counts.get(plugin_name, 0) + 1
        self._plugin_fault_counts[plugin_name] = count
        self._plugin_last_faults[plugin_name] = message
        self._record_error(
            "plugin",
            "fault",
            message,
            exc,
            plugin=plugin_name,
            event=event,
            task=task,
        )

        if count < self.config.plugin_faults.max_failures:
            return

        await self._disable_plugin(
            plugin_name,
            f"disabled after {count} fault(s): {message}",
        )
        await self._disable_dependent_plugins(plugin_name)
        await self._set_state(ControllerState.DEGRADED, f"plugin {plugin_name} disabled")

    async def _disable_dependent_plugins(self, dependency_name: str) -> None:
        for plugin in list(self._registry.all()):
            if dependency_name in plugin.required_plugins:
                await self._disable_plugin(
                    plugin.name,
                    f"required plugin {dependency_name} was disabled",
                )
                await self._disable_dependent_plugins(plugin.name)

    async def _disable_plugin(self, plugin_name: str, reason: str) -> None:
        plugin = self._registry.remove(plugin_name)
        self._plugin_disabled_reasons[plugin_name] = reason
        self._plugin_statuses[plugin_name] = PluginLifecycleStatus.DISABLED
        logger.error(
            "Plugin disabled: %s (%s)",
            plugin_name,
            reason,
            extra={"plugin": plugin_name, "reason": reason},
        )

        await self.tasks.cancel_owner(plugin_name)
        if plugin is not None:
            await self._teardown_plugin(plugin)
        self._plugin_statuses[plugin_name] = PluginLifecycleStatus.DISABLED

    def _track_discovered_plugins(self, plugins: list[Plugin[Any]]) -> None:
        for plugin in plugins:
            self._known_plugins[plugin.name] = plugin
            self._plugin_statuses[plugin.name] = PluginLifecycleStatus.DISCOVERED

    async def _setup_plugins(self, plugins: list[Plugin[Any]]) -> None:
        for plugin in plugins:
            self._plugin_statuses[plugin.name] = PluginLifecycleStatus.SETUP_STARTED
            try:
                await plugin.setup()
            except Exception as exc:
                self._plugin_statuses[plugin.name] = PluginLifecycleStatus.FAILED
                self._record_error(
                    "plugin",
                    f"{plugin.name}.setup",
                    f"Plugin '{plugin.name}' setup failed",
                    exc,
                )
                logger.exception("Plugin setup failed for %s", plugin.name)
                raise

            self._registry.register(plugin)
            self._plugin_statuses[plugin.name] = PluginLifecycleStatus.READY

    async def _rollback_plugin_setup(self) -> None:
        for plugin in reversed(list(self._known_plugins.values())):
            status = self._plugin_statuses.get(plugin.name)
            if status is PluginLifecycleStatus.READY:
                await self._teardown_plugin(plugin)
            elif status in {
                PluginLifecycleStatus.SETUP_STARTED,
                PluginLifecycleStatus.FAILED,
            }:
                plugin.cleanup_registered_side_effects()

    async def _teardown_plugin(self, plugin: Plugin[Any]) -> None:
        if self._plugin_statuses.get(plugin.name) is PluginLifecycleStatus.TORN_DOWN:
            return

        self._plugin_statuses[plugin.name] = PluginLifecycleStatus.TEARDOWN_STARTED
        try:
            await plugin.teardown()
        except Exception as exc:
            self._record_error(
                "plugin",
                f"{plugin.name}.teardown",
                f"Plugin '{plugin.name}' teardown failed",
                exc,
            )
            logger.exception("Plugin teardown failed for %s", plugin.name)
        finally:
            plugin.cleanup_registered_side_effects()
            self._plugin_statuses[plugin.name] = PluginLifecycleStatus.TORN_DOWN

    async def _connect_gbx_for_startup(self) -> None:
        reconnect = self.config.reconnect
        delay = reconnect.initial_delay_seconds
        started_at = asyncio.get_running_loop().time()

        while True:
            try:
                await self.gbx.connect()
                return
            except AuthenticationError:
                raise
            except asyncio.CancelledError:
                raise
            except OSError as exc:
                if not reconnect.enabled:
                    raise

                if self._reconnect_time_exceeded(started_at):
                    raise _ReconnectTimeoutError(
                        "Initial GBX connection retry time exceeded"
                    ) from exc

                logger.warning(
                    "Initial GBX connection failed (%s); retrying in %.1f second(s)",
                    exc,
                    self._next_reconnect_sleep(started_at, delay),
                )
                await asyncio.sleep(self._next_reconnect_sleep(started_at, delay))
                delay = min(delay * reconnect.multiplier, reconnect.max_delay_seconds)
            except Exception:
                if not reconnect.enabled:
                    raise

                if self._reconnect_time_exceeded(started_at):
                    raise _ReconnectTimeoutError("Initial GBX connection retry time exceeded")

                logger.exception(
                    "Initial GBX connection failed unexpectedly; retrying in %.1f second(s)",
                    self._next_reconnect_sleep(started_at, delay),
                )
                await asyncio.sleep(self._next_reconnect_sleep(started_at, delay))
                delay = min(delay * reconnect.multiplier, reconnect.max_delay_seconds)

    async def _check_capabilities(self) -> None:
        checks: list[CapabilityCheck] = []

        async def run_check(name: str, call: Any, *, required: bool = True) -> None:
            try:
                result = await call()
            except Exception as exc:
                message = str(exc)
                checks.append(CapabilityCheck(name=name, ok=False, message=message))
                self._record_error("gbx", "capability", f"Capability check failed: {name}", exc)
                if required:
                    raise
                return

            checks.append(CapabilityCheck(name=name, ok=True, message=repr(result)))

        try:
            await run_check("GetVersion", self.gbx.get_version)
            await run_check("GetSystemInfo", self.gbx.get_system_info)
            await run_check("GetStatus", self.gbx.get_status)
            if self.gbx.chat_router is not None:
                await run_check(
                    "ChatEnableManualRouting",
                    lambda: self.gbx.chat_enable_manual_routing(True, False),
                )
        finally:
            self._capability_checks = checks

    async def _gbx_supervision_loop(self) -> None:
        reconnect = self.config.reconnect
        delay = reconnect.initial_delay_seconds
        retry_started_at: float | None = None

        while True:
            try:
                if not self.gbx.connected:
                    if retry_started_at is None:
                        retry_started_at = asyncio.get_running_loop().time()

                    if self._reconnect_time_exceeded(retry_started_at):
                        logger.error(
                            "GBX reconnect retry time exceeded %.1f second(s); shutting down",
                            reconnect.max_retry_time_seconds,
                        )
                        await self._set_state(
                            ControllerState.FAILED,
                            "GBX reconnect retry time exceeded",
                        )
                        self._request_shutdown()
                        return

                    await self._sleep_before_gbx_reconnect(
                        self._next_reconnect_sleep(retry_started_at, delay)
                    )
                    if self._reconnect_time_exceeded(retry_started_at):
                        logger.error(
                            "GBX reconnect retry time exceeded %.1f second(s); shutting down",
                            reconnect.max_retry_time_seconds,
                        )
                        await self._set_state(
                            ControllerState.FAILED,
                            "GBX reconnect retry time exceeded",
                        )
                        self._request_shutdown()
                        return

                    try:
                        await self.gbx.connect()
                    except OSError as exc:
                        self._record_error("gbx", "reconnect", "GBX reconnect attempt failed", exc)
                        logger.warning("GBX reconnect attempt failed: %s", exc)
                        delay = min(delay * reconnect.multiplier, reconnect.max_delay_seconds)
                        continue
                    else:
                        retry_started_at = None
                        delay = reconnect.initial_delay_seconds
                        await self._set_state(
                            ControllerState.PLUGINS_READY,
                            "GBX session reconnected",
                        )

                await self.gbx.listen(self.bus)
                raise ConnectionClosed("GBX listener ended")
            except asyncio.CancelledError:
                raise
            except AuthenticationError:
                await self._set_state(ControllerState.FAILED, "GBX authentication failed")
                logger.exception("GBX authentication failed; reconnect supervision stopped")
                raise
            except (ConnectionClosed, OSError) as exc:
                await self._set_state(ControllerState.DEGRADED, "GBX session disconnected")
                self._record_error("gbx", "listen", "GBX session disconnected", exc)
                logger.warning("GBX session disconnected: %s", exc)
                await self.gbx.disconnect()

                if not reconnect.enabled:
                    await self._set_state(ControllerState.FAILED, "GBX reconnect disabled")
                    logger.error("GBX reconnect is disabled; supervision stopped")
                    return

                retry_started_at = asyncio.get_running_loop().time()
                delay = reconnect.initial_delay_seconds
            except Exception:
                await self._set_state(ControllerState.DEGRADED, "GBX listener failed")
                self._record_error("gbx", "listen", "GBX session ended unexpectedly")
                logger.exception("GBX session ended unexpectedly")
                await self.gbx.disconnect()

                if not reconnect.enabled:
                    await self._set_state(ControllerState.FAILED, "GBX reconnect disabled")
                    logger.error("GBX reconnect is disabled; supervision stopped")
                    return

                if retry_started_at is None:
                    retry_started_at = asyncio.get_running_loop().time()

                delay = min(delay * reconnect.multiplier, reconnect.max_delay_seconds)

    async def _sleep_before_gbx_reconnect(self, delay: float) -> None:
        logger.info("Reconnecting to GBX in %.1f second(s)", delay)
        await asyncio.sleep(delay)

    def _next_reconnect_sleep(self, started_at: float, delay: float) -> float:
        reconnect = self.config.reconnect
        elapsed = asyncio.get_running_loop().time() - started_at
        remaining = max(0.0, reconnect.max_retry_time_seconds - elapsed)
        return min(delay, remaining)

    def _reconnect_time_exceeded(self, started_at: float) -> bool:
        elapsed = asyncio.get_running_loop().time() - started_at
        return elapsed >= self.config.reconnect.max_retry_time_seconds

    def _request_shutdown(self) -> None:
        if self._shutdown_event is not None:
            self._shutdown_event.set()

    async def _stop_gbx_supervision(self) -> None:
        if self._gbx_task is None:
            return

        self._gbx_task.cancel()
        try:
            await self._gbx_task
        except asyncio.CancelledError:
            pass
        self._gbx_task = None

    async def _tick_loop(self) -> None:
        loop = asyncio.get_running_loop()
        next_tick = loop.time() + 1.0

        try:
            while True:
                await asyncio.sleep(max(0.0, next_tick - loop.time()))
                await self.bus.emit(ControllerTick())

                now = loop.time()
                next_tick += 1.0
                if next_tick <= now:
                    next_tick = now + 1.0
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Controller tick loop failed")

    async def _stop_tick_loop(self) -> None:
        if self._tick_task is None:
            return

        self._tick_task.cancel()
        try:
            await self._tick_task
        except asyncio.CancelledError:
            pass
        self._tick_task = None

    def plugin(self, name: str) -> Plugin[Any] | None:
        return self._registry.get(name)

    def register_chat_command(
        self,
        plugin_name: str,
        name: str,
        *,
        description: str = "",
        usage: str | None = None,
        aliases: Iterable[str] = (),
    ) -> ChatCommandRegistration:
        return self.chat.register_command(
            plugin_name,
            name,
            description=description,
            usage=usage,
            aliases=aliases,
        )

    def chat_commands(self) -> list[ChatCommandRegistration]:
        return self.chat.commands()

    def register_chat_router(self, plugin_name: str, handler: ChatRouterHandler) -> None:
        self.chat.register_route_handler(plugin_name, handler)

    @classmethod
    def run(cls, config_path: str = "trackhelm.toml") -> None:
        config = TrackHelmConfig.from_file(Path(config_path))

        level_name = config.logging.level.upper()
        level = logging.getLevelNamesMapping().get(level_name, logging.INFO)

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
            if self._shutdown_event is None:
                self._shutdown_event = asyncio.Event()
            await self._shutdown_event.wait()
        except KeyboardInterrupt:
            pass
        except asyncio.CancelledError:
            pass
        except _ReconnectTimeoutError as exc:
            logger.error("%s; shutting down", exc)
        finally:
            await self.stop()
