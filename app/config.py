import json
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    APP_NAME: str = "Data Management API"
    SKIP_HEADER_CHECK: bool = False
    MOCK_USER_EMAIL: str = "test@example.com"
    MOCK_USER_GROUPS_JSON: str = '[]'

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str

    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "data-storage"
    MINIO_USE_SSL: bool = False

    @property
    def MOCK_USER_GROUPS(self) -> List[str]:
        try:
            return json.loads(self.MOCK_USER_GROUPS_JSON)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse MOCK_USER_GROUPS_JSON: {self.MOCK_USER_GROUPS_JSON}")
            return []

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
