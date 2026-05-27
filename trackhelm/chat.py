from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Iterable
from dataclasses import dataclass
import inspect
import logging
import shlex
from typing import TYPE_CHECKING

from trackhelm.eventbus.events import ChatCommand
from trackhelm.eventbus.events import PlayerChat


if TYPE_CHECKING:
    from trackhelm.eventbus.bus import EventBus


logger = logging.getLogger(__name__)


ChatForwarder = Callable[[str, str, str], Awaitable[bool]]
ChatRouterHandler = Callable[["ChatRoute"], Awaitable[None] | None]


class ChatCommandRegistrationError(ValueError):
    """Raised when plugin chat command metadata cannot be registered."""


@dataclass(frozen=True, slots=True)
class ChatCommandRegistration:
    """Metadata for a chat command provided by a plugin."""

    name: str
    plugin: str
    description: str = ""
    usage: str | None = None
    aliases: tuple[str, ...] = ()


@dataclass(slots=True)
class ChatRoute:
    """Mutable context passed to plugins before normal chat is forwarded."""

    player_uid: int
    login: str
    original_text: str
    text: str
    destination: str = ""
    cancelled: bool = False

    def cancel(self) -> None:
        """Prevent this chat message from being forwarded publicly."""

        self.cancelled = True


class ChatRouter:
    """Coordinates command events, command metadata, and manual chat forwarding."""

    def __init__(
        self,
        event_bus: EventBus,
        forward_message: ChatForwarder,
        *,
        handler_timeout: float = 10.0,
    ) -> None:
        self._event_bus = event_bus
        self._forward_message = forward_message
        self._handler_timeout = handler_timeout
        self._commands: dict[str, ChatCommandRegistration] = {}
        self._registrations: list[ChatCommandRegistration] = []
        self._route_handlers: list[tuple[str, ChatRouterHandler]] = []

    def register_command(
        self,
        plugin: str,
        name: str,
        *,
        description: str = "",
        usage: str | None = None,
        aliases: Iterable[str] = (),
    ) -> ChatCommandRegistration:
        normalized_name = self._normalize_command_name(name)
        normalized_aliases = tuple(self._normalize_command_name(alias) for alias in aliases)

        if normalized_name in normalized_aliases:
            raise ChatCommandRegistrationError(
                f"Plugin '{plugin}' registered chat command '{normalized_name}' as its own alias"
            )

        seen_aliases: set[str] = set()
        for alias in normalized_aliases:
            if alias in seen_aliases:
                raise ChatCommandRegistrationError(
                    f"Plugin '{plugin}' registered duplicate alias '{alias}'"
                )
            seen_aliases.add(alias)

        for command_key in (normalized_name, *normalized_aliases):
            existing = self._commands.get(command_key)
            if existing is not None:
                raise ChatCommandRegistrationError(
                    "Chat command "
                    f"'{command_key}' from plugin '{plugin}' conflicts with plugin "
                    f"'{existing.plugin}'"
                )

        registration = ChatCommandRegistration(
            name=normalized_name,
            plugin=plugin,
            description=description,
            usage=usage,
            aliases=normalized_aliases,
        )

        self._registrations.append(registration)
        for command_key in (normalized_name, *normalized_aliases):
            self._commands[command_key] = registration

        return registration

    def commands(self) -> list[ChatCommandRegistration]:
        return list(self._registrations)

    def register_route_handler(self, plugin: str, handler: ChatRouterHandler) -> None:
        self._route_handlers.append((plugin, handler))

    async def route_player_chat(self, event: PlayerChat) -> None:
        if event.text.startswith("/"):
            await self._event_bus.emit(self._build_command_event(event))
            return

        route = ChatRoute(
            player_uid=event.player_uid,
            login=event.login,
            original_text=event.text,
            text=event.text,
        )
        await self._run_route_handlers(route)

        if route.cancelled:
            return

        await self._forward_message(route.text, route.login, route.destination)
        event = PlayerChat(
            player_uid=event.player_uid,
            login=event.login,
            text=route.text,
            is_registred_cmd=event.is_registred_cmd,
        )

        await self._event_bus.emit(event)

    async def _run_route_handlers(self, route: ChatRoute) -> None:
        for plugin, handler in self._route_handlers:
            if route.cancelled:
                return

            try:
                result = handler(route)
                if inspect.isawaitable(result):
                    await asyncio.wait_for(result, timeout=self._handler_timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    "Chat router timeout for plugin=%s handler=%s",
                    plugin,
                    getattr(handler, "__name__", repr(handler)),
                )
            except Exception:
                logger.exception(
                    "Chat router failed for plugin=%s handler=%s",
                    plugin,
                    getattr(handler, "__name__", repr(handler)),
                )

    def _build_command_event(self, event: PlayerChat) -> ChatCommand:
        command_text = event.text[1:].strip()
        command_part, separator, remainder = command_text.partition(" ")
        command = command_part.lower()
        args = self._split_args(remainder) if separator else []

        return ChatCommand(
            player_uid=event.player_uid,
            login=event.login,
            text=event.text,
            command=command,
            args=args,
        )

    def _split_args(self, value: str) -> list[str]:
        try:
            return shlex.split(value)
        except ValueError:
            logger.warning("Failed to parse quoted chat command args: %r", value)
            return value.split()

    def _normalize_command_name(self, value: str) -> str:
        command = value.strip().removeprefix("/").lower()
        if not command:
            raise ChatCommandRegistrationError("Chat command names cannot be empty")
        if any(char.isspace() for char in command):
            raise ChatCommandRegistrationError(
                f"Chat command names cannot contain whitespace: {value!r}"
            )
        return command
