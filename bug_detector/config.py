"""Configuration management and secure environment variable access."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Automatically load .env if it exists, without raising if absent
load_dotenv(override=False)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "history.db"


class Settings:
    """Application settings read from environment variables."""

    @property
    def openai_api_key(self) -> Optional[str]:
        key = os.getenv("OPENAI_API_KEY", "").strip()
        return key if key else None

    @property
    def openai_model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    @property
    def db_path(self) -> Path:
        env_path = os.getenv("DB_PATH")
        if env_path:
            p = Path(env_path)
            return p if p.is_absolute() else (BASE_DIR / p)
        return DEFAULT_DB_PATH

    @property
    def app_host(self) -> str:
        return os.getenv("APP_HOST", "127.0.0.1").strip()

    @property
    def app_port(self) -> int:
        try:
            return int(os.getenv("APP_PORT", "8000").strip())
        except ValueError:
            return 8000

    @property
    def masked_api_key(self) -> str:
        """Return masked version of OpenAI API key for safe diagnostics."""
        key = self.openai_api_key
        if not key:
            return "Not configured"
        if len(key) <= 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"


settings = Settings()
