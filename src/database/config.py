import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

user = os.getenv("DATABASE_USER")
password = os.getenv("DATABASE_PASSWORD")
db_name = os.getenv("DATABASE_NAME")


class Settings(BaseSettings):
    sqlalchemy_database_url: str = (
        f"postgresql+asyncpg://{user}:{password}@localhost:5432/{db_name}"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Функция получает настройки из класса Settings
    """
    return Settings()