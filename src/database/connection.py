from typing import Annotated

from fastapi import Depends
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.sqlalchemy_database_url,
    poolclass=NullPool,
)

AsyncSessionLocal = async_sessionmaker(
    autocommit=False, expire_on_commit=False, autoflush=False, bind=engine
)


async def get_session() -> AsyncSession:
    """
    Асинхронная функция, которая подключается к сессии
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


DBSession = Annotated[AsyncSessionLocal, Depends(get_session)]
session = DBSession()