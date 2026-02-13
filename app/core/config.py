# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Union
import os

class Settings(BaseSettings):
    PORT: int = Field(default=8000)
    CORS_ORIGINS: Union[str, list[str]] = Field(default="http://localhost:3000")

    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    # Last.fm - try to get from env directly if .env parsing fails
    LASTFM_API_KEY: str = Field(default_factory=lambda: os.getenv("LASTFM_API_KEY", ""))
    LASTFM_BASE_URL: str = "https://ws.audioscrobbler.com/2.0/"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Warn if API key is missing, but don't block startup
        if not self.LASTFM_API_KEY or self.LASTFM_API_KEY == "your_api_key_here":
            import warnings
            warnings.warn(
                "LASTFM_API_KEY is not set. Recommendation endpoints will not work.\n"
                "Please set it in your .env file: LASTFM_API_KEY=your_api_key_here\n"
                "Get your API key from: https://www.last.fm/api/account/create",
                UserWarning
            )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = True

settings = Settings()
