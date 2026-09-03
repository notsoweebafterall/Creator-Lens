from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str
    gemini_model: str

    db_path: str = "./data/creators.db"
    vector_store_path: str = "./data/vector_store"
    guidelines_dir: str = "./data/guidelines"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def db_file(self) -> Path:
        return Path(self.db_path)

    @property
    def vector_store_dir(self) -> Path:
        return Path(self.vector_store_path)

    @property
    def guidelines_dir_path(self) -> Path:
        return Path(self.guidelines_dir)


settings = Settings()