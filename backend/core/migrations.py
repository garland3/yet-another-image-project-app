from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from .config import settings
from .database import AsyncSessionLocal
from .schemas import UserCreate
from utils.crud import create_user, get_user_by_email

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parents[1]


def _sync_database_url(url: str) -> str:
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("+aiosqlite", "", 1)
    if url.startswith("postgresql+asyncpg"):
        return url.replace("+asyncpg", "+psycopg2", 1)
    return url


def _alembic_config() -> Config:
    cfg = Config(str(_BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BASE_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", _sync_database_url(settings.DATABASE_URL))
    cfg.attributes["configure_logger"] = False
    return cfg


async def check_and_apply_migrations() -> None:
    """Check database schema version and apply migrations if needed."""
    cfg = _alembic_config()
    loop = asyncio.get_running_loop()

    # Get current database version
    current_version = await loop.run_in_executor(None, _get_current_db_version, cfg)

    # Get target version (latest migration)
    target_version = await loop.run_in_executor(None, _get_target_version, cfg)

    logger.info(f"Database schema check - Current: {current_version or 'None'}, Target: {target_version}")

    if current_version == target_version:
        logger.info("Database schema is up to date")
        await _ensure_mock_user()
        return

    if current_version is None:
        logger.info("Fresh database detected - applying all migrations")
    else:
        logger.warning(f"Database schema version mismatch!")
        logger.warning(f"  Current version: {current_version}")
        logger.warning(f"  Expected version: {target_version}")
        logger.warning("  Applying migrations to bring database up to date...")

    # Apply migrations
    await loop.run_in_executor(None, command.upgrade, cfg, "head")

    # Verify the migration succeeded
    new_version = await loop.run_in_executor(None, _get_current_db_version, cfg)
    if new_version != target_version:
        logger.error(f"❌ CRITICAL: Migration failed!")
        logger.error(f"  Expected version: {target_version}")
        logger.error(f"  Actual version: {new_version}")
        logger.error("  Database may be in an inconsistent state")
        sys.exit(1)

    logger.info(f"✅ Database migrations completed successfully - now at version: {new_version}")
    await _ensure_mock_user()


def _get_current_db_version(cfg: Config) -> str | None:
    """Get the current database version from the alembic_version table."""
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row else None
    except Exception:
        # Table doesn't exist or other error - fresh database
        return None


def _get_target_version(cfg: Config) -> str:
    """Get the latest migration version (head) from migration scripts."""
    script_dir = ScriptDirectory.from_config(cfg)
    return script_dir.get_current_head()


# Backwards compatibility alias
async def run_migrations() -> None:
    """Legacy alias for check_and_apply_migrations."""
    await check_and_apply_migrations()


async def _ensure_mock_user() -> None:
    if not settings.SKIP_HEADER_CHECK:
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_email(db=session, email=settings.MOCK_USER_EMAIL)
        if user is not None:
            logger.debug("Mock user already present", extra={"email": settings.MOCK_USER_EMAIL})
            return

        payload = UserCreate(email=settings.MOCK_USER_EMAIL, groups=settings.MOCK_USER_GROUPS)
        await create_user(db=session, user=payload)
        logger.info("Created mock user", extra={"email": settings.MOCK_USER_EMAIL})


if __name__ == "__main__":
    asyncio.run(run_migrations())
