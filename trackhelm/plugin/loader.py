from __future__ import annotations

from graphlib import CycleError
from graphlib import TopologicalSorter
from importlib.metadata import entry_points
import logging
from pathlib import Path
from typing import Any

import tomli
import tomli_w

from .base import Plugin
from .config import PluginConfig


logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "trackhelm.plugins"


class PluginNotInstalledError(RuntimeError):
    """Raised when a requested plugin dependency is not installed."""


class PluginCycleError(RuntimeError):
    """Raised when plugin dependencies contain a cycle."""


def discover_plugins() -> dict[str, type[Plugin[Any]]]:
    """Discover installed plugin entry points."""

    available: dict[str, type[Plugin[Any]]] = {}

    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            loaded = ep.load()
        except Exception:
            logger.exception("Failed to load plugin entry point %s", ep.name)
            continue

        if not isinstance(loaded, type) or not issubclass(loaded, Plugin):
            logger.warning(
                "Skipping entry point %s because it did not resolve to a Plugin subclass",
                ep.name,
            )
            continue

        available[ep.name] = loaded

    return available


def _missing_plugin_error(key: str) -> PluginNotInstalledError:
    package_name = f"trackhelm-{key.replace('_', '-')}"
    return PluginNotInstalledError(
        f"Plugin '{key}' is not installed. Install it with: pip install {package_name}"
    )


def _resolve_dependencies(
    requested: set[str],
    available: dict[str, type[Plugin[Any]]],
) -> set[str]:
    enabled = set(requested)
    pending = list(requested)

    while pending:
        key = pending.pop()
        cls = available.get(key)
        if cls is None:
            raise _missing_plugin_error(key)

        for dependency in cls.required_plugins:
            if dependency not in available:
                raise _missing_plugin_error(dependency)

            if dependency not in enabled:
                enabled.add(dependency)
                pending.append(dependency)

    return enabled


def _topological_sort(
    enabled: set[str],
    available: dict[str, type[Plugin[Any]]],
) -> list[str]:
    graph = {
        key: {
            dependency for dependency in available[key].required_plugins if dependency in enabled
        }
        for key in enabled
    }

    try:
        return list(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        cycle = exc.args[1] if len(exc.args) > 1 else ()
        cycle_names = ", ".join(str(name) for name in cycle) or ", ".join(sorted(enabled))
        raise PluginCycleError(f"Plugin dependency cycle detected: {cycle_names}") from exc


def _build_plugin_config(cls: type[Plugin[Any]], raw: dict[str, Any]) -> PluginConfig:
    return cls.config_class(**raw)


def _merge_defaults(defaults: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(raw)

    for key, value in defaults.items():
        if key not in merged:
            merged[key] = value
        elif isinstance(value, dict) and isinstance(merged[key], dict):
            merged[key] = _merge_defaults(value, merged[key])

    return merged


def _sync_plugin_config(key: str, cls: type[Plugin[Any]], plugins_dir: Path) -> None:
    """Write missing plugin config defaults without overwriting user values."""

    config_path = plugins_dir / f"{key}.toml"
    if not config_path.exists():
        return

    try:
        defaults = cls.config_class().model_dump(mode="python")
    except Exception:
        logger.exception("Failed to build default config for plugin %s", key)
        return

    raw: dict[str, Any] = {}
    if config_path.exists():
        try:
            with config_path.open("rb") as fh:
                loaded = tomli.load(fh)
            if isinstance(loaded, dict):
                raw = loaded
        except Exception:
            logger.exception("Failed to read plugin config file %s", config_path)
            return

    merged = _merge_defaults(defaults, raw)
    if merged == raw:
        return

    with config_path.open("wb") as fh:
        tomli_w.dump(merged, fh)


async def load_enabled_plugins(controller: Any) -> list[Plugin[Any]]:
    """Instantiate all enabled plugins in dependency order."""

    available = discover_plugins()
    requested = set(controller.config.plugins.enabled)
    enabled = _resolve_dependencies(requested, available)
    order = _topological_sort(enabled, available)

    plugins: list[Plugin[Any]] = []

    for key in order:
        cls = available[key]
        _sync_plugin_config(key, cls, Path("plugins"))

        plugin = cls()
        plugin.controller = controller
        plugin._config = _build_plugin_config(cls, controller.config.plugin_config(key))
        plugins.append(plugin)

        suffix = "" if key in requested else " (auto-activated)"
        logger.info("Loaded plugin: %s%s", key, suffix)

    return plugins
