from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    # Required
    POSTGRES_USER: str = Field(..., min_length=1, description="Database username")
    POSTGRES_PASSWORD: SecretStr = Field(..., description="Database password")
    POSTGRES_DB: str = Field(..., min_length=1, description="Database name")

    # Optional with safe defaults
    POSTGRES_HOST: str = Field(default="localhost", description="Database host")
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535, description="Database port")

    # Optional consolidated URL; if provided, it takes precedence for direct usage
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Full SQLAlchemy database URL. If absent, one is constructed from individual fields.",
    )

    # SQLAlchemy pool tuning
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=50)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    DB_POOL_RECYCLE: int = Field(default=1800, ge=60, le=86400)
    SQLALCHEMY_ECHO: bool = Field(default=False)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    def build_sqlalchemy_url(self) -> str:
        """
        Returns a SQLAlchemy-style URL compatible with psycopg2 driver.
        Respects an explicit `DATABASE_URL` if set; otherwise constructs one.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        pwd = self.POSTGRES_PASSWORD.get_secret_value()
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{pwd}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache(maxsize=1)
def get_settings() -> DatabaseSettings:
    """
    Load and cache settings from environment/.env, raising on invalid or missing fields.
    """
    try:
        return DatabaseSettings()  # type: ignore[call-arg]
    except ValidationError as e:
        # Re-raise with a clearer message for operational visibility
        raise RuntimeError(f"Invalid or missing database configuration: {e}") from e