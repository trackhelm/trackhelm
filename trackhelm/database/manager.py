from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession

from .base import Base
from .base import make_engine
from .base import make_session_factory


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage the application's async engine and session factory."""

    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = make_engine(url)
        self._session_factory = make_session_factory(self.engine)

    async def initialize(self) -> None:
        """Create all tables registered on Base.metadata.

        This must be called after all model modules (including plugin models)
        have been imported so their tables are registered.
        """

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield an `AsyncSession` with an open transaction.

        The transaction is committed on normal exit and rolled back on
        exception. The session is closed when the context exits.
        """

        session = self._session_factory()
        try:
            async with session.begin():
                yield session
        except Exception:
            # session.begin() will rollback, ensure session is closed and re-raise
            await session.close()
            raise
        else:
            await session.close()

    async def dispose(self) -> None:
        """Dispose of the engine and its connection pool."""

        await self.engine.dispose()

    async def check_reachable(self) -> None:
        """Run a lightweight query to verify database reachability."""

        async with self.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
