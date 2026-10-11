from datetime import datetime
from functools import lru_cache
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    database_url: str = Field(min_length=1)
    secret_key: SecretStr
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    timezone: str = "Europe/Berlin"


@lru_cache
def get_settings() -> Settings:
    load_dotenv(ROOT_DIR / ".env")
    secret = os.environ.get("SECRET_KEY", "")
    if len(secret) < 32:
        raise RuntimeError("Set SECRET_KEY to a random value of at least 32 characters.")
    settings = Settings(
        database_url=os.environ.get("DATABASE_URL", ""),
        secret_key=SecretStr(secret),
        access_token_expire_minutes=os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"),
        timezone=os.environ.get("APP_TIMEZONE", "Europe/Berlin"),
    )
    ZoneInfo(settings.timezone)
    return settings


def business_today():
    return datetime.now(ZoneInfo(get_settings().timezone)).date()