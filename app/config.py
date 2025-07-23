from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "Data Management API"
    SKIP_HEADER_CHECK: bool = False
    CHECK_MOCK_MEMBERSHIP: bool = True
    MOCK_USER_EMAIL: str = "test@example.com"
    MOCK_USER_GROUPS_JSON: str = '["admin-group", "data-scientists", "project-alpha-group"]'
    AUTH_SERVER_URL: Optional[str] = None

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5433
    DATABASE_URL: str

    # S3/MinIO settings - made optional with defaults for local development
    S3_ENDPOINT: str = "localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadminpassword"
    S3_BUCKET: str = "data-storage"
    S3_USE_SSL: bool = False

    # Frontend build path configuration
    FRONTEND_BUILD_PATH: str = "frontend/build"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = "allow"
    
    @property
    def MOCK_USER_GROUPS(self):
        import json
        return json.loads(self.MOCK_USER_GROUPS_JSON)

settings = Settings()
