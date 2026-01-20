from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=False,
        extra="ignore",
    )

    DEBUG: bool = False

    PROJECT_NAME: str
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # Local DBs
    VECTOR_DB_PATH: str
    DOC_DIR_PATH: str
    DATABASE_URL: str

    LANGSMITH_API_KEY: SecretStr
    LANGSMITH_TRACING: bool = False

    OPENAI_API_KEY: SecretStr | None
    GEMINI_API_KEY: SecretStr | None

    # OAuth settings
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: SecretStr

    # Frontend URL for CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # Logging settings
    LOG_SAMPLE_RATE: float = 0.1
    LOG_SLOW_THRESHOLD_MS: int = 1000  # Slow request threshold in ms

    # GCP | BQ Configuration
    GCP_PROJECT_ID: str
    BQ_DATASET_NAME: str
    BQ_TABLE_NAME: str
    BQ_DATASET_LOCATION: str
    EMBEDDING_DIM: int = 768


settings = Settings()  # type: ignore
