from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import AsyncGenerator
from .config import settings

# Use aiosqlite for SQLite URLs to support async operations
database_url = settings.DATABASE_URL
if database_url.startswith('sqlite:'):
    # Convert sqlite:// to sqlite+aiosqlite:// for async support
    database_url = database_url.replace('sqlite:', 'sqlite+aiosqlite:', 1)

engine = create_async_engine(
    database_url,
    echo=False,
    future=True
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

