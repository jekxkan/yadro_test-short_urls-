from typing import List, Optional

from fastapi import HTTPException, Depends, APIRouter, Query
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from pydantic_core import Url
from starlette.responses import RedirectResponse

from src.tables import schemas
from src.tables.schemas import UrlStatistic
from src.tables.urls import urls_service, urls_statistics_service
from src.tables.users import users_service

router = APIRouter()
security = HTTPBasic()

async def authentication(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Аутентифицирует пользователя с использованием Basic-аутентификации

    Args:
        credentials (HTTPBasicCredentials, optional): учётные данные пользователя,
            автоматически получаемые через Depends от объекта security

    Returns:
        user: объект аутентифицированного пользователя,
        возвращаемый из users_service.auth_user
    """
    user = await users_service.auth_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="User not exists")
    return user

@router.post("/create-short-url", response_model=schemas.Url)
async def create_url(origin_url: str, user = Depends(authentication)):
    """
    Роут для создания коротких ссылкок для переданного оригинального
    ресурса после аутентификации пользователя

    Args:
        - origin_url(str): оригинальный ресурс
        - user: текущий аутентифицированный пользователь

    Returns:
        - short_url(schemas.Url): сформированная короткая ссылка
    """
    short_url = await urls_service.create_new_url(origin_url, user.id)
    return short_url

@router.get("/get_short_urls", response_model=List[str])
async def get_short_urls(user = Depends(authentication),
                         is_active: bool = Query(
                             description='Вывести только активные?'),
                         limit:
                         Optional[int] = Query(
                             None, ge=1,
                             description='Кол-во ссылок,'
                                         'при отсутствии '
                                         'значения выведутся '
                                         'все ссылки'),
                         offset:
                         Optional[int] = Query(
                             None, ge=1,
                             description='С какой ссылки по порядку '
                                         'начать вывод,'
                                         'при отсутствии '
                                         'значения - вывод '
                                         'с 1-ой ссылки')):
    """"
    Роут для получения списка коротких ссылок(с фильтрацией и пагинацией)

    Args:
        - user: аутентифицированный пользователь
        - is_active (bool): параметр фильтрации(False - получить все ссылки,
          True - только активные)
        - limit (Optional[int]): при установке знаечния выведется только введенное
                                количество(default = None(выводятся все))
        - offset (Optional[int]): при установке значения вывод начнется с ссылки 
                                 под введенным номером(default = None(начинается с первой))
    """
    urls_list = await urls_service.get_short_urls(is_active, limit, offset)
    return urls_list

@router.get("/get_statistics", response_model=List[UrlStatistic])
async def get_url_statistics(user = Depends(authentication)):
    """
    Роут для получения статистики по коротким ссылкам
    (переходы по ним за последний час/день)

    Args:
        - user: аутентифицированный пользователь

    Returns:
        - urls_statistics(List[UrlStatistic]): список объектов статистики для всех
                                       коротких ссылок, отсортированный
                                       по убыванию переходов за
                                       последний день
    """
    urls_statistics = await urls_statistics_service.get_full_stat()
    return urls_statistics

@router.get("/{short_url_key}", response_model=Url)
async def redirect_to_original_url(short_url_key: str):
    """
    Перенаправляет пользователя с короткой ссылки на оригинальный ресурс

    Args:
        - short_url_key(str): сформированное уникальное дополнение функцией form_url
                              для короткой ссылки

    Returns:
        - RedirectResponse: перенаправление на оригинальный ресурс
    """
    try:
        url = await urls_service.get_origin_url(short_url_key)
        await urls_service.add_url_click(short_url_key)
        return RedirectResponse(url.origin_url)
    except Exception:
        raise HTTPException(status_code=404, detail="Original not found")