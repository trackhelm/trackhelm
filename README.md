[![trackhelm logo](https://raw.githubusercontent.com/trackhelm/trackhelm/main/docs/image/trackhelm-icon.png)](https://github.com/trackhelm/trackhelm)

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
