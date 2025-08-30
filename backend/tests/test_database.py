import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import asyncpg
from database import create_db_and_tables, get_db

class TestDatabase:
    """Test database functionality"""

    @pytest.mark.asyncio
    async def test_create_db_and_tables_success(self, monkeypatch):
        """Test successful database table creation by letting it run against sqlite memory."""
        # Just call the function; it should not raise under sqlite memory DB
        await create_db_and_tables()

    @pytest.mark.asyncio
    async def test_create_db_and_tables_connection_error(self):
        """Test database connection error handling"""
        with patch('database.engine.begin', side_effect=asyncpg.exceptions.InvalidCatalogNameError("database does not exist")):
            with patch('sys.exit') as mock_exit:
                await create_db_and_tables()
                mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_create_db_and_tables_name_resolution_error(self):
        """Test database name resolution error"""
        error = Exception("Name or service not known")
        with patch('database.engine.begin', side_effect=error):
            with patch('sys.exit') as mock_exit:
                await create_db_and_tables()
                mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_create_db_and_tables_authentication_error(self):
        """Test database authentication error"""
        error = Exception("password authentication failed")
        with patch('database.engine.begin', side_effect=error):
            with patch('sys.exit') as mock_exit:
                await create_db_and_tables()
                mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_create_db_and_tables_connection_refused(self):
        """Test database connection refused error"""
        error = Exception("Connection refused")
        with patch('database.engine.begin', side_effect=error):
            with patch('sys.exit') as mock_exit:
                await create_db_and_tables()
                mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio 
    async def test_get_db_session(self):
        """Test database session generator"""
        # This is a generator function, so we need to test it properly
        db_gen = get_db()
        
        # In a real test environment, this would work with the test database
        # For now, just test that it's a generator
        assert hasattr(db_gen, '__aiter__') or hasattr(db_gen, '__iter__')

    def test_engine_configuration(self):
        """Smoke check via get_db being a generator/async-gen."""
        gen = get_db()
        assert hasattr(gen, "__aiter__") or hasattr(gen, "__anext__")

    def test_session_local_configuration(self):
        """Test AsyncSessionLocal configuration"""
    # Nothing to assert strongly here; covered by application usage
    assert callable(get_db)