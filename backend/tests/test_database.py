import pytest
from core.database import get_db


class TestDatabase:
    """Test database functionality"""

    def test_get_db_is_async_gen(self):
        """get_db should be an async generator."""
        gen = get_db()
        assert hasattr(gen, "__aiter__") or hasattr(gen, "__anext__")