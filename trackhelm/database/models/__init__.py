"""Compatibility package for TrackHelm database models.

The core currently ships with no built-in SQLAlchemy models. Plugins that
define tables should import their model modules before
``DatabaseManager.initialize()`` runs so their metadata is registered.
"""

__all__: list[str] = []
