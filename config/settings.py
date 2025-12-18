from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

class DatabaseSettings(BaseSettings):
    POSTGRES_USER: str = Field(..., min_length=1)
    POSTGRES_PASSWORD: SecretStr = Field(...)
    POSTGRES_DB: str = Field(..., min_length=1)
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    DATABASE_URL: Optional[str] = Field(default=None)
    
    DB_POOL_SIZE: int = Field(default=3, ge=1, le=50)
    DB_MAX_OVERFLOW: int = Field(default=5, ge=0, le=100)
    DB_POOL_RECYCLE: int = Field(default=1800, ge=300)
    SQLALCHEMY_ECHO: bool = Field(default=False)
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }

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
    """Load database settings from Streamlit secrets or environment variables."""
    
    # Try Streamlit secrets FIRST (AWS deployment)
    try:
        import streamlit as st
        
        # Check if secrets exist and have database section
        if hasattr(st, 'secrets'):
            secrets_dict = dict(st.secrets)
            
            if 'database' in secrets_dict:
                logger.info("✅ Loading database settings from Streamlit secrets")
                db_secrets = secrets_dict['database']
                
                # Convert to dict if needed
                if hasattr(db_secrets, '_dict'):
                    db_secrets = db_secrets._dict
                elif hasattr(db_secrets, 'to_dict'):
                    db_secrets = db_secrets.to_dict()
                else:
                    db_secrets = dict(db_secrets)
                
                # Create settings from secrets
                return DatabaseSettings(**db_secrets)
            else:
                logger.warning("⚠️ Streamlit secrets found but no 'database' section")
        else:
            logger.warning("⚠️ Streamlit imported but st.secrets not available")
            
    except ImportError:
        logger.info("ℹ️ Streamlit not available (non-Streamlit context)")
    except ValidationError as e:
        logger.error(f"❌ Invalid Streamlit secrets format: {e}")
        raise RuntimeError(
            "Streamlit secrets are configured but invalid. "
            "Please check your secrets.toml format."
        ) from e
    except Exception as e:
        logger.warning(f"⚠️ Could not load Streamlit secrets: {e}")
    
    # Fall back to environment variables (.env file for local development)
    logger.info("ℹ️ Falling back to environment variables")
    
    try:
        # Get environment variables with type checking
        postgres_user = os.getenv("POSTGRES_USER")
        postgres_password = os.getenv("POSTGRES_PASSWORD")
        postgres_db = os.getenv("POSTGRES_DB")
        postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        
        # Check if required env vars exist
        if not postgres_user or not postgres_password or not postgres_db:
            missing = []
            if not postgres_user:
                missing.append("POSTGRES_USER")
            if not postgres_password:
                missing.append("POSTGRES_PASSWORD")
            if not postgres_db:
                missing.append("POSTGRES_DB")
                
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Please configure database credentials in Streamlit secrets or .env file."
            )
        
        # Create settings from environment (now guaranteed non-None)
        return DatabaseSettings(
            POSTGRES_USER=postgres_user,
            POSTGRES_PASSWORD=SecretStr(postgres_password),
            POSTGRES_DB=postgres_db,
            POSTGRES_HOST=postgres_host,
            POSTGRES_PORT=int(postgres_port),
        )
        
    except (ValidationError, ValueError) as e:
        logger.error(
            "❌ Database configuration failed!\n"
            "Please configure credentials in:\n"
            "  - Streamlit Cloud: Settings → Secrets\n"
            "  - Local development: .env file"
        )
        logger.error(f"Error details: {e}")
        raise RuntimeError(
            "Database configuration not found. "
            "Configure credentials in Streamlit secrets or .env file."
        ) from e