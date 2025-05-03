import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.crud import create_user, get_user_by_username
from app.config import settings

async def create_test_user():
    """
    Create a test user in the database if it doesn't already exist.
    This user will be used for development and testing purposes.
    """
    async with AsyncSessionLocal() as session:
        # Check if the user already exists
        existing_user = await get_user_by_username(session, settings.MOCK_USER_EMAIL)
        if existing_user:
            print(f"Test user '{settings.MOCK_USER_EMAIL}' already exists.")
            return existing_user
        
        # Create the test user
        user_id = settings.MOCK_USER_EMAIL  # Using email as ID for simplicity
        username = settings.MOCK_USER_EMAIL  # Using email as username for simplicity
        user = await create_user(session, user_id, username)
        print(f"Created test user: {user.id}")
        return user

if __name__ == "__main__":
    asyncio.run(create_test_user())
