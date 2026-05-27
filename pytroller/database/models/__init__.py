"""Database models package.

Import submodules here so importing ``pytroller.database.models`` also
registers the individual model modules (e.g. ``user``) for metadata
registration side-effects.
"""

from __future__ import annotations

from .user import User


__all__ = ["User"]
