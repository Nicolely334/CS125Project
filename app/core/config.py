# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PORT: int = Field(default=8000)
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str

    # Last.fm
    LASTFM_API_KEY: str
    LASTFM_SHARED_SECRET: str | None = None
    LASTFM_BASE_URL: str = "https://ws.audioscrobbler.com/2.0/"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
