from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

class DatabaseSettings(BaseSettings):
    # AWS Streamlit uses st.secrets, not environment variables
    POSTGRES_USER: str = Field(..., min_length=1)
    POSTGRES_PASSWORD: SecretStr = Field(...)
    POSTGRES_DB: str = Field(..., min_length=1)
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    DATABASE_URL: Optional[str] = Field(default=None)
    
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=50)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    DB_POOL_RECYCLE: int = Field(default=1800, ge=300)
    SQLALCHEMY_ECHO: bool = Field(default=False)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def build_sqlalchemy_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        pwd = self.POSTGRES_PASSWORD.get_secret_value()
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{pwd}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            f"?sslmode=require"
        )

def get_db_settings() -> DatabaseSettings:
    """Load database settings from environment or Streamlit secrets."""
    # Try Streamlit secrets first (AWS deployment)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'database' in st.secrets:
            logger.info("Loading database settings from Streamlit secrets")
            return DatabaseSettings(**st.secrets['database'])
    except ImportError:
        # Streamlit not available (testing/CLI context)
        pass
    except ValidationError as e:
        logger.error(f"Invalid Streamlit secrets configuration: {e}")
        raise
    except Exception as e:
        logger.warning(f"Failed to load Streamlit secrets: {e}")
    
    # Fall back to environment variables (.env file)
    try:
        logger.info("Loading database settings from environment variables")
        
        # Get environment variables
        postgres_user = os.getenv("POSTGRES_USER", "")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "")
        postgres_db = os.getenv("POSTGRES_DB", "")
        postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        
        # Validate required fields before creating settings
        if not postgres_user or not postgres_password or not postgres_db:
            raise ValueError(
                "Missing required database credentials: "
                f"POSTGRES_USER={'✓' if postgres_user else '✗'}, "
                f"POSTGRES_PASSWORD={'✓' if postgres_password else '✗'}, "
                f"POSTGRES_DB={'✓' if postgres_db else '✗'}"
            )
        
        # Create DatabaseSettings with SecretStr for password
        settings = DatabaseSettings(
            POSTGRES_USER=postgres_user,
            POSTGRES_PASSWORD=SecretStr(postgres_password),  # Wrap in SecretStr
            POSTGRES_DB=postgres_db,
            POSTGRES_HOST=postgres_host,
            POSTGRES_PORT=postgres_port,
        )
        return settings
    except (ValidationError, ValueError) as e:
        logger.error(
            "Database configuration missing or invalid! "
            "Ensure .env file exists or Streamlit secrets are configured."
        )
        logger.error(f"Configuration errors: {e}")
        raise RuntimeError(
            "Database configuration not found. "
            "Please configure database credentials in .env or Streamlit secrets."
        ) from e