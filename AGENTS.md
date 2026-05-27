# AGENTS.md

## Project Purpose

`trackhelm` is an asyncio-based Python controller for a TrackMania dedicated
server that speaks the GBXRemote XML-RPC protocol. Its job is to run beside a
game server, authenticate with an admin account, enable server callbacks, expose
typed helpers for XML-RPC methods, and give plugins a clean way to react to
server events.

The project is intentionally shaped as a small core plus plugins:

- The core owns configuration, logging, the GBXRemote connection, event
  dispatch, database access, and plugin lifecycle.
- Plugins own optional behavior such as chat commands, welcome messages,
  moderation workflows, statistics, or server automation.
- The controller keeps running until interrupted, while callbacks from the game
  server are translated into events and delivered to plugin handlers.

Think of the repository as the foundation for a modern Python alternative to an
event-driven TrackMania server controller: keep the core reliable and generic,
then put server-specific features into plugins.

## How The Application Starts

The entry points are `example.py` and `python -m trackhelm`. Both call
`Controller.run()` from `trackhelm/controller.py`.

Startup flow:

1. `Controller.run()` loads `trackhelm.toml` through
  `TrackHelmConfig.from_file()`. The config class has been renamed to
  `TrackHelmConfig`, which is the top-level trackhelm config model.
2. Logging is configured by `trackhelm/logging.py` with stdout logging and a
  rotating file handler at `logs/trackhelm.log`.
3. `Controller` creates the core services:
   - `EventBus`
   - `DatabaseManager`
   - `GbxClient`
   - `PluginRegistry`
4. `Controller.start()` connects to the TrackMania server through GBXRemote.
5. Enabled plugins are discovered, dependency-sorted, instantiated, configured,
   and set up.
6. The database is initialized after any plugin models are imported and before
   plugin setup completes.
7. The GBX listener task runs continuously and feeds callbacks into the event
   bus.
8. Shutdown tears down plugins in reverse registration order, cancels the GBX
   listener, disconnects the GBX client, stops the event bus, and disposes the
   database engine.

`Controller._main()` then waits forever on an `asyncio.Event()` until the
process is interrupted or cancelled.

## Configuration

The default config file is `trackhelm.toml`.

Important sections:

- `[server]`: GBXRemote host, port, admin login, and password.
- `[database]`: SQLAlchemy async database URL, for example
  `sqlite+aiosqlite:///./trackhelm.db`.
- `[logging]`: log level, log directory, rotation size, and backup count.
- `[plugins]`: list of enabled plugin keys.

Plugin config can be supplied in two places:

- Inline as `[plugins.<key>]` in `trackhelm.toml`.
- As `plugins/<key>.toml`.

File-based plugin config wins over inline config. The loader also tries to sync
missing default values into an existing `plugins/<key>.toml` without overwriting
user-provided values.

The `plugins/` directory is ignored by `.gitignore` and is suitable for local
plugin packages or local plugin config files. Do not assume local plugin
contents are versioned unless `git ls-files` says they are.

## Core Module Map

`trackhelm/controller.py`

- Coordinates the whole application.
- Owns the event bus, database manager, GBX client, and active plugin registry.
- Exposes `controller.plugin(name)` to retrieve an active plugin.

`trackhelm/config.py`

- Defines Pydantic config models for server, database, logging, and plugins.
- Loads TOML with `tomllib`.
- Stores raw plugin config dictionaries privately and exposes them through
  `plugin_config(key)`.

`trackhelm/logging.py`

- Sets the root logger level.
- Clears existing handlers.
- Adds stdout and rotating file handlers with a shared formatter.

`trackhelm/gbx/`

- Implements the GBXRemote protocol client.
- `protocol.py` packs and unpacks GBXRemote headers.
- `codec.py` encodes and decodes XML-RPC payloads.
- `client.py` owns the TCP connection, handshake, authentication, callback
  listener, request futures, timeouts, and shutdown behavior.
- `methods.py` contains typed wrappers around many GBX XML-RPC methods.
- `models.py` contains dataclasses that coerce dynamic XML-RPC dictionaries into
  typed Python objects.
- `exceptions.py` defines GBX-specific error types.

`trackhelm/eventbus/`

- Provides an asyncio queue with worker tasks.
- Supports both legacy string-named events and typed event dataclasses.
- `events.py` registers typed TrackMania callback events with
  `@register_event("TrackMania.SomeCallback")`.
- Handlers may be synchronous or async; async results are awaited with a timeout.

`trackhelm/database/`

- Provides a shared SQLAlchemy async declarative base.
- `DatabaseManager.initialize()` creates all tables registered on
  `Base.metadata`.
- `DatabaseManager.session()` yields an `AsyncSession` inside a transaction,
  committing on normal exit and rolling back on exception.
- The core currently ships with no built-in database tables. Plugins can
  register their own models on the shared declarative base.

`trackhelm/plugin/`

- Defines the plugin API, plugin config base class, entry point discovery,
  dependency resolution, plugin registry, and optional Alembic migration helper.

## GBXRemote Behavior

`GbxClient` is the low-level bridge to the dedicated server.

Connection behavior:

- Opens an asyncio TCP connection.
- Reads the GBXRemote handshake and verifies the `GBXRemote 2` header.
- Starts an internal listener task.
- Authenticates with `Authenticate`.
- Enables callbacks with `EnableCallbacks`.

Request behavior:

- `GbxClient.call(method, params)` XML-RPC encodes the request.
- Protocol v2 request handles are created by setting the high bit.
- A pending `Future` is stored by handle until the response arrives.
- Response packets resolve the corresponding future.
- Request timeouts raise `RequestTimeout`.
- Shutdown fails outstanding futures with `ConnectionClosed`.

Callback behavior:

- Callback packets are identified by protocol handle convention.
- `TrackMania.PlayerChat` is routed through the controller-owned chat router
  when running through `Controller`. Manual chat routing is enabled, slash
  commands are kept private, and normal chat is forwarded after plugin routing
  hooks run.
- If a callback name has a registered typed event class, the client builds that
  dataclass with `from_gbx_params()` and emits it.
- If typed conversion fails or no event class exists, the client emits a legacy
  raw event by name with `params`.

When adding GBX behavior, prefer a typed wrapper in `methods.py` plus a model in
`models.py` when the response shape is known. Use `gbx.call()` directly only for
unmodeled or experimental XML-RPC methods.

## Event Model

Typed events inherit from `BaseEvent` in `trackhelm/eventbus/events.py`.

To add a new typed callback:

```python
@register_event("TrackMania.CallbackName")
@dataclass(slots=True)
class CallbackName(BaseEvent):
    field_one: str
    field_two: int
```

`BaseEvent.from_gbx_params()` maps positional GBX callback parameters to
dataclass fields in annotation order. It can also convert dicts into model
dataclasses when annotations refer to classes from `trackhelm.gbx.models`.

Plugins should prefer typed subscriptions:

```python
self.subscribe(PlayerConnect, self._handle_player_connect)
```

Use string subscriptions only when a typed event does not exist yet.

## Controller Tick Event

`ControllerTick` is a typed internal event with the name
`TrackHelm.ControllerTick`. It has no fields and is emitted by the controller
once per second while the controller is running.

Plugins that need shared one-second timer behavior can subscribe to it in
`setup()`:

```python
self.subscribe(ControllerTick, self._handle_tick)
```

The heartbeat task starts after plugin setup and GBX listener scheduling, and it
is cancelled before plugin teardown. If the event loop is delayed, missed ticks
are skipped rather than replayed in a burst. Plugins with custom intervals or
plugin-private timing should still own their own `asyncio.Task` and cancel it in
`teardown()`.

## Chat Commands And Manual Routing

`ChatCommand` is a typed controller event, not a raw GBX callback. It is emitted
when a player's chat text starts with `/`. Slash commands are not forwarded to
public chat and are not also emitted as `PlayerChat`.

`ChatCommand` fields:

- `player_uid`: player id from the chat callback.
- `login`: player login.
- `text`: original slash-prefixed message.
- `command`: lowercased command name without `/`.
- `args`: shell-like parsed argument list, so quoted phrases stay together.

Plugins should register command metadata during `setup()` and then subscribe to
`ChatCommand` like any other typed event:

```python
self.register_chat_command("hello", description="Send a greeting.", usage="/hello [name]")
self.subscribe(ChatCommand, self._handle_chat_command)
```

The controller stores command metadata in `controller.chat_commands()` for
future help dialogs. Command names and aliases are normalized to lowercase
without a leading slash. Duplicate command names or aliases across plugins are
startup errors.

Plugins can also participate in normal-message manual routing with
`self.register_chat_router(handler)`. Routing handlers receive a mutable
`ChatRoute` with `player_uid`, `login`, `original_text`, mutable `text`, mutable
`destination`, `cancelled`, and `cancel()`. Routers run in plugin setup order.
They may adjust text, change the destination, or cancel the message before it is
forwarded. Routing hooks apply only to normal chat, not slash commands.

## Plugin System

Plugins are discovered through Python package entry points in the group
`trackhelm.plugins`.

Plugin packages should expose entries like:

```toml
[project.entry-points."trackhelm.plugins"]
welcome = "trackhelm_welcome.plugin:WelcomePlugin"
```

A plugin class should:

- Subclass `Plugin[YourConfig]`.
- Return its entry point key from `name`.
- Set `config_class` when it needs configuration.
- Optionally declare `required_plugins` and `optional_plugins`.
- Subscribe to events in `setup()`.
- Clean up external resources in `teardown()`.

The base plugin gives handlers access to:

- `self.controller`
- `self.config`
- `self.gbx`
- `self.db`
- `self.subscribe(...)`
- `self.register_chat_command(...)`
- `self.register_chat_router(...)`

Plugin dependency behavior:

- Enabled plugin keys come from `trackhelm.toml`.
- Required plugin dependencies are auto-activated.
- Missing plugins raise an install hint like `pip install trackhelm-<key>`.
- Dependency cycles raise `PluginCycleError`.
- Setup order is topological.
- Teardown order is reverse registry order.

Plugin config classes should inherit from `PluginConfig`. The base config is
frozen and ignores unknown fields, which makes plugin config tolerant of extra
TOML keys while keeping runtime values immutable.

For database-using plugins, import models before `DatabaseManager.initialize()`
needs them. Plugins that need schema migrations can use `PluginMigration`, which
runs Alembic migrations against the shared async engine with a plugin-specific
version table.

## Database Conventions

Use `async with self.db.session() as session:` inside plugins and controller
code. The context manager already opens a transaction and closes the session.

Store plugin-specific state in plugin-owned tables rather than expecting core
tables from the controller package.

- When adding models:

- Inherit from `trackhelm.database.base.Base`.
- Add imports in an appropriate `models/__init__.py` so metadata registration
  happens before table creation.
- Use SQLAlchemy async APIs from application code.

## Development Workflow

The package targets Python 3.14+ and is typed via `trackhelm/py.typed`.

Useful commands:

```powershell
.\venv\Scripts\python.exe -m trackhelm
.\venv\Scripts\python.exe -m compileall trackhelm
.\venv\Scripts\ruff.exe check .
.\venv\Scripts\ruff.exe format .
.\venv\Scripts\mypy.exe trackhelm
```

Running the application requires a reachable TrackMania dedicated server with
GBXRemote enabled and credentials matching `trackhelm.toml`.

The pre-commit configuration runs Ruff check with fixes, Ruff format, and mypy.
There is no test suite in this checkout yet, so use compile, lint, type checks,
and focused manual or integration checks when changing behavior.

## Design Guidelines For Future Changes

- Keep the core generic. Features that are optional or server-community-specific
  should become plugins.
- Keep the event loop non-blocking. Use asyncio-compatible libraries or move
  blocking work away from callback handlers.
- Preserve GBX protocol details carefully. Header size, handle matching,
  callback detection, and request future cleanup are central to correctness.
- Prefer typed events and typed GBX models when the shape is known.
- Preserve the legacy raw event path so unmodeled callbacks still work.
- Keep plugin setup and teardown idempotent where possible.
- Avoid importing plugin packages in core code except through entry points.
- Treat plugin configuration as user-owned data. Merge defaults without
  overwriting explicit settings.
- Keep database sessions short and scoped to a transaction.
- Do not commit generated runtime logs, virtual environments, or local plugin
  experiments unless the repository intentionally starts tracking them.

## Current Repository Notes

-- The config class name `TrackHelmConfig` replaces the previous `PysecoConfig` name.
