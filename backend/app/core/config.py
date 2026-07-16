from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    scrapecreators_api_key: str
    scrapecreators_base_url: str = "https://api.scrapecreators.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
