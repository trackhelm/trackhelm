from __future__ import annotations

from typing import Any

from .base import Plugin


class PluginRegistry:
    """In-memory registry of active plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin[Any]] = {}

    def register(self, plugin: Plugin[Any]) -> None:
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> Plugin[Any] | None:
        return self._plugins.get(name)

    def remove(self, name: str) -> Plugin[Any] | None:
        return self._plugins.pop(name, None)

    def all(self) -> list[Plugin[Any]]:
        return list(self._plugins.values())
