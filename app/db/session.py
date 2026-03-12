# ABOUTME: SQLAlchemy async engine and session factory for PostgreSQL.
# ABOUTME: Provides get_session for FastAPI and task_session for Celery workers.

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


@asynccontextmanager
async def task_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a session with a fresh engine for use in Celery tasks.

    Each asyncio.run() call creates a new event loop, so we need a new
    engine each time to avoid cross-loop Future errors.
    """
    task_engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(task_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await task_engine.dispose()
