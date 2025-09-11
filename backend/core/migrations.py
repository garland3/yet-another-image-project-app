import asyncio
from sqlalchemy import text
from .database import engine, AsyncSessionLocal
from .models import Base
from .config import settings
from utils.crud import get_user_by_email, create_user
from .schemas import UserCreate

async def run_migrations():
    """
    Run database migrations to add new tables and relationships.
    This function should be called during application startup.
    """
    print("Running database migrations...")
    
    # Create all tables defined in models.py
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create a mock user if it doesn't exist
    await create_mock_user()
    
    # Migrate existing data
    await migrate_existing_data()

    # Add deletion / audit structures
    await add_image_deletion_features()
    
    print("Database migrations completed successfully.")

async def create_mock_user():
    """Create a mock user if it doesn't exist."""
    if not settings.SKIP_HEADER_CHECK:
        # Only create mock user if header check is skipped
        return
    
    async with AsyncSessionLocal() as session:
        # Check if mock user exists
        mock_user = await get_user_by_email(db=session, email=settings.MOCK_USER_EMAIL)
        
        if not mock_user:
            # Create mock user
            user_create = UserCreate(
                email=settings.MOCK_USER_EMAIL,
                groups=settings.MOCK_USER_GROUPS,
            )
            await create_user(db=session, user=user_create)
            print(f"Created mock user: {settings.MOCK_USER_EMAIL}")
        else:
            print(f"Mock user already exists: {settings.MOCK_USER_EMAIL}")

async def migrate_existing_data():
    """Migrate existing data to the new schema."""
    async with AsyncSessionLocal() as session:
        # Update existing DataInstance records to link to User records
        await migrate_data_instances(session)


async def migrate_data_instances(session):
    """
    Migrate existing DataInstance records to link to User records.
    This function finds all DataInstance records with a non-null uploaded_by_user_id
    and links them to the corresponding User record.
    """
    # Check if the uploader_id column exists
    column_exists = False
    try:
        async with engine.begin() as conn:
            try:
                # Try to select from the column to see if it exists
                await conn.execute(text("SELECT uploader_id FROM data_instances LIMIT 1"))
                column_exists = True
            except Exception:
                column_exists = False
    except Exception as e:
        print(f"Error checking if uploader_id column exists: {str(e)}")
        return
    
    # If the column doesn't exist, add it
    if not column_exists:
        try:
            print("Adding uploader_id column to data_instances table...")
            async with engine.begin() as conn:
                await conn.execute(
                    text("ALTER TABLE data_instances ADD COLUMN uploader_id UUID REFERENCES users(id)")
                )
            print("Added uploader_id column to data_instances table")
        except Exception as e:
            print(f"Error adding uploader_id column: {str(e)}")
            return
    
    try:
        # Get all unique uploaded_by_user_id values
        result = await session.execute(
            text("SELECT DISTINCT uploaded_by_user_id FROM data_instances WHERE uploaded_by_user_id IS NOT NULL")
        )
        user_ids = [row[0] for row in result.fetchall()]
        
        for email in user_ids:
            # Find or create user
            user = await get_user_by_email(db=session, email=email)
            
            if not user:
                # Create user
                user_create = UserCreate(
                    email=email,
                    groups=[],  # Default empty groups
                )
                user = await create_user(db=session, user=user_create)
                print(f"Created user for migration: {email}")
            
            # Update DataInstance records
            await session.execute(
                text("UPDATE data_instances SET uploader_id = :user_id WHERE uploaded_by_user_id = :email"),
                {"user_id": str(user.id), "email": email}
            )
        
        # Commit the changes
        await session.commit()
        print(f"Migrated {len(user_ids)} unique users in DataInstance records")
        
    except Exception as e:
        await session.rollback()
        print(f"Error migrating data instances: {str(e)}")
        raise

async def add_image_deletion_features():
    """Add soft delete columns and image_deletion_events table if they do not exist."""
    async with engine.begin() as conn:
        # Check and add columns to data_instances
        column_checks = {
            'deleted_at': "ALTER TABLE data_instances ADD COLUMN deleted_at TIMESTAMPTZ",
            'deleted_by_user_id': "ALTER TABLE data_instances ADD COLUMN deleted_by_user_id UUID REFERENCES users(id)",
            'deletion_reason': "ALTER TABLE data_instances ADD COLUMN deletion_reason TEXT",
            'pending_hard_delete_at': "ALTER TABLE data_instances ADD COLUMN pending_hard_delete_at TIMESTAMPTZ",
            'hard_deleted_at': "ALTER TABLE data_instances ADD COLUMN hard_deleted_at TIMESTAMPTZ",
            'hard_deleted_by_user_id': "ALTER TABLE data_instances ADD COLUMN hard_deleted_by_user_id UUID REFERENCES users(id)",
            'storage_deleted': "ALTER TABLE data_instances ADD COLUMN storage_deleted BOOLEAN NOT NULL DEFAULT FALSE"
        }
        for col, ddl in column_checks.items():
            try:
                await conn.execute(text(f"SELECT {col} FROM data_instances LIMIT 1"))
            except Exception:
                try:
                    await conn.execute(text(ddl))
                    print(f"Added column {col} to data_instances")
                except Exception as e:
                    print(f"Failed adding column {col}: {e}")

        # Create image_deletion_events table if missing
        try:
            await conn.execute(text("SELECT 1 FROM image_deletion_events LIMIT 1"))
        except Exception:
            try:
                await conn.execute(text(
                    """
                    CREATE TABLE image_deletion_events (
                        id UUID PRIMARY KEY,
                        image_id UUID NOT NULL REFERENCES data_instances(id),
                        project_id UUID NOT NULL REFERENCES projects(id),
                        actor_user_id UUID NULL REFERENCES users(id),
                        action VARCHAR(32) NOT NULL,
                        reason TEXT NULL,
                        storage_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                        previous_state JSON NULL,
                        at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                ))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_image_deletion_events_image_time ON image_deletion_events (image_id, at DESC)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_image_deletion_events_project_time ON image_deletion_events (project_id, at DESC)"))
                print("Created image_deletion_events table and indexes")
            except Exception as e:
                print(f"Failed creating image_deletion_events table: {e}")

if __name__ == "__main__":
    # Run migrations when script is executed directly
    asyncio.run(run_migrations())
