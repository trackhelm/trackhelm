"""Shared SQLAlchemy declarative base and helpers.

Provides a single `Base` declarative base class and helpers to create an
async engine and session factory for the application and plugins.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Common declarative base for all models."""


def make_engine(url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine for the given URL.

    The function creates the engine with reasonable defaults for an
    asyncio-enabled application.
    """

    return create_async_engine(url, future=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an `async_sessionmaker` bound to `engine`.

    The returned factory can be called to produce `AsyncSession` instances.
    """

    return async_sessionmaker(bind=engine, expire_on_commit=False)
