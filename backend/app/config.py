from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./silkworm.db"
    sensor_update_interval: int = 2
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]


settings = Settings()
