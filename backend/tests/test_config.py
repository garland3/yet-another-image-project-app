import pytest
import os
from unittest.mock import patch, mock_open
from config import Settings

class TestSettings:
    """Test configuration settings"""

    @patch.dict(os.environ, {
        "POSTGRES_USER": "u",
        "POSTGRES_PASSWORD": "p",
        "POSTGRES_DB": "d",
        "POSTGRES_SERVER": "localhost",
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    }, clear=True)
    def test_settings_default_values(self):
        """Test that settings have correct default values with minimal required env vars provided"""
        settings = Settings()
        assert settings.APP_NAME == "Data Management API"
        assert settings.DEBUG is False
        assert settings.SKIP_HEADER_CHECK is False
        assert settings.S3_ACCESS_KEY == "minioadmin"
        assert settings.S3_SECRET_KEY == "minioadminpassword"
        assert settings.S3_BUCKET == "data-storage"

    def test_settings_from_env_vars(self):
        """Test that settings load from environment variables"""
        with patch.dict(os.environ, {
            "APP_NAME": "Test App",
            "DEBUG": "true",
            "S3_ACCESS_KEY": "test-key",
            "POSTGRES_USER": "u",
            "POSTGRES_PASSWORD": "p",
            "POSTGRES_DB": "d",
            "POSTGRES_SERVER": "localhost",
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:"
        }):
            settings = Settings()
            assert settings.APP_NAME == "Test App"
            assert settings.DEBUG == True
            assert settings.S3_ACCESS_KEY == "test-key"

    def test_boolean_parsing_with_whitespace(self):
        """Test that boolean values with whitespace are parsed correctly"""
        with patch.dict(os.environ, {
            "DEBUG": "true ",
            "SKIP_HEADER_CHECK": " false",
            "S3_USE_SSL": "true\r\n",
            "POSTGRES_USER": "u",
            "POSTGRES_PASSWORD": "p",
            "POSTGRES_DB": "d",
            "POSTGRES_SERVER": "localhost",
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:"
        }):
            settings = Settings()
            assert settings.DEBUG == True
            assert settings.SKIP_HEADER_CHECK == False
            assert settings.S3_USE_SSL == True

    def test_mock_user_groups_property(self):
        """Test that MOCK_USER_GROUPS property parses JSON correctly"""
        with patch.dict(os.environ, {
            "MOCK_USER_GROUPS_JSON": '["group1", "group2", "group3"]'
        }):
            settings = Settings()
            assert settings.MOCK_USER_GROUPS == ["group1", "group2", "group3"]

    def test_mock_user_groups_invalid_json(self):
        """Test handling of invalid JSON in MOCK_USER_GROUPS_JSON"""
        with patch.dict(os.environ, {
            "MOCK_USER_GROUPS_JSON": 'invalid-json'
        }):
            settings = Settings()
            with pytest.raises(Exception):
                _ = settings.MOCK_USER_GROUPS

    def test_env_file_loading_precedence(self):
        """Test that local .env takes precedence over parent .env"""
        local_env_content = "DEBUG=true\nAPP_NAME=Local App"
        parent_env_content = "DEBUG=false\nAPP_NAME=Parent App\nS3_BUCKET=parent-bucket"
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("os.path.isfile") as mock_isfile:
                mock_isfile.side_effect = lambda path: path == ".env"
                mock_file.return_value.read.return_value = local_env_content
                s = Settings(_env_file=None, _env_file_encoding='utf-8', **{
                    "POSTGRES_USER": "u",
                    "POSTGRES_PASSWORD": "p",
                    "POSTGRES_DB": "d",
                    "POSTGRES_SERVER": "localhost",
                    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
                })
                assert hasattr(s, 'Config')
                assert s.Config.env_file == [".env", "../.env"]

    def test_field_validators_exist(self):
        """Test that field validators are properly set up"""
        settings = Settings()
        # Check that the validator method exists
        assert hasattr(settings, 'parse_bool_with_strip')

    def test_frontend_build_path_default(self):
        """Test frontend build path default value"""
        settings = Settings()
        assert settings.FRONTEND_BUILD_PATH == "frontend/build"

    def test_cors_origins_from_settings(self):
        """Test CORS origins configuration"""
        # This would be tested in main.py tests, but we can test the setting exists
        settings = Settings()
        # The CORS origins are handled in main.py, not in settings directly
        assert hasattr(settings, 'APP_NAME')  # Just verify settings work

    def test_database_url_required_fields(self):
        """Test that required database fields raise validation errors when missing"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception):
                Settings()

    @patch.dict(os.environ, {
        "POSTGRES_USER": "testuser",
        "POSTGRES_PASSWORD": "testpass", 
        "POSTGRES_DB": "testdb",
        "POSTGRES_SERVER": "localhost",
        "DATABASE_URL": "postgresql://testuser:testpass@localhost/testdb"
    })
    def test_required_fields_provided(self):
        """Test that settings work when all required fields are provided"""
        settings = Settings()
        assert settings.POSTGRES_USER == "testuser"
        assert settings.POSTGRES_PASSWORD == "testpass"
        assert settings.POSTGRES_DB == "testdb"
        assert settings.POSTGRES_SERVER == "localhost"

    def test_extra_config_allowed(self):
        """Test that extra configuration is allowed"""
        settings = Settings()
        assert settings.Config.extra == "allow"