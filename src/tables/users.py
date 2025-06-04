import asyncio

from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.database.connection import session
from src.tables.models import Users

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UsersService:
    """
    Сервис для управления пользователями: регистрация и аутентификация
    """
    def __init__(self):
        """
        Инициализация сервиса с сессией базы данных

        Args:
            session: асинхронная сессия
        """
        self.session = session

    async def create_user(self, username: str, user_password: str) -> Users:
        """
        Создает нового пользователя с хешированным паролем

        Args:
            username(str): имя пользователя
            user_password(str): пароль пользователя

        Returns:
            Users: объек таблицы users
        """
        try:
            hashed_password = pwd_context.hash(user_password)
            user = Users(username=username, hashed_password=hashed_password)
            self.session.add(user)
            await self.session.commit()
            return user
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=400,
                detail="User with this username already exists"
            )

    async def auth_user(self, user_name: str,
                        user_password: str) -> Users:
        """
        Аутентифицирует пользователя по имени и паролю

        Args:
            user_name(str): имя пользователя
            user_password(str): пароль пользователя

        Returns:
            Users: объект таблицы users(аутентифицированный пользователь)
        """
        stmt = (
            select(Users)
            .filter_by(username=user_name)
        )
        user = (await self.session.execute(stmt)).scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not pwd_context.verify(user_password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid password")

        return user

users_service = UsersService()

name = 'user'
password = '12345'
if __name__ == '__main__':
    asyncio.run(users_service.create_user(username=name, user_password=password))