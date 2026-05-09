from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
DOTENV_PATH = BASE_DIR / ".env"

load_dotenv(DOTENV_PATH)




class Settings(BaseModel):
    database_url: str = Field(min_length=1)
    secret_key: str = Field(min_length=1)
    algorithm: str = Field(default="HS256", min_length=1)
    access_token_expire_minutes: int = Field(default=30, ge=1)
    base_url: str = Field(default="http://localhost:8000", min_length=1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    required_keys = ("DATABASE_URL", "SECRET_KEY")
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if missing_keys:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing_keys)
        )

    return Settings(
        database_url=os.environ["DATABASE_URL"],
        secret_key=os.environ["SECRET_KEY"],
        algorithm=os.getenv("ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        base_url=os.getenv("BASE_URL", "http://localhost:8000"),
    )
