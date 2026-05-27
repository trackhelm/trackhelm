[![trackhelm banner](https://raw.githubusercontent.com/trackhelm/trackhelm/main/docs/image/trackhelm-banner.png)](https://github.com/trackhelm/trackhelm)

TrackHelm
========

trackhelm is an asyncio-based Python controller for a TrackMania dedicated
server that implements the GBXRemote XML-RPC protocol. It runs alongside a
game server, authenticates with an admin account, enables server callbacks,
exposes typed helpers for GBX XML-RPC methods, and gives plugins a clean,
typed way to react to server events.

Purpose
-------

The project provides a small, reliable core that handles connection management,
callback dispatch, configuration, and database integration so server-maintainers
and plugin authors can focus on features (chat commands, moderation rules,
welcome messages, statistics, automation) instead of low-level protocol code.

Key ideas
---------

- Minimal core: keep the foundation small and stable; optional behaviors live
  in plugins.
- Typed events: GBX callbacks are translated into typed dataclasses whenever
  possible, making handlers clearer and safer.
- Chat routing: slash-prefixed chat is kept private as command events, while
  normal messages can be adjusted by plugins before public forwarding.
- Async-first: all I/O and plugin hooks are asyncio-compatible to avoid
  blocking the event loop.
- Plugin-friendly: plugins are discovered and loaded via entry points and
  run in a predictable lifecycle with dependency ordering and teardown.

Core components
---------------

- `GbxClient` — TCP connection, handshake, authentication, request/response
  futures, and the callback listener.
- `EventBus` — asynchronous event dispatch with support for typed events and
  string-named legacy events.
- `DatabaseManager` — async SQLAlchemy integration and scoped transactional
  sessions for plugins and the core.
- `PluginRegistry` / plugin API — discovery, dependency resolution, setup and
  teardown lifecycles for plugins.

Chat commands
-------------

TrackHelm enables GBX manual chat routing when run through the controller.
Messages starting with `/` are not forwarded to public chat. Instead, they are
emitted as typed `ChatCommand` events with the original text, a lowercased
command name, and shell-like parsed `args`.

Plugins can register command metadata for future help dialogs and subscribe to
the command event:

```python
from trackhelm.eventbus.events import ChatCommand

async def setup(self) -> None:
    self.register_chat_command("hello", description="Send a greeting.", usage="/hello [name]")
    self.subscribe(ChatCommand, self._handle_chat_command)
```

Plugins can also participate in normal chat routing with
`self.register_chat_router(...)`. Routers receive a mutable `ChatRoute` and may
adjust `route.text`, change `route.destination`, or call `route.cancel()` before
the controller forwards the message.

When to use trackhelm
----------------------

Use this project when you want to build server-side logic for a TrackMania
dedicated server without reimplementing GBXRemote protocol details. It's
well-suited for adding moderation, automation, metrics, and community-facing
features as modular plugins.

Where to look next
------------------

See the `trackhelm` package for implementation details and `example.py` or
running `python -m trackhelm` for the simple entrypoint used during
development. Plugin examples live in the `plugins/` directory.

License
-------

This repository is released under the terms found in the `LICENSE` file.
