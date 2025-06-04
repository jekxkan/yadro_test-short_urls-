import random
import re
import string
from datetime import datetime, timedelta
from typing import List

import pytz
from fastapi import HTTPException
from sqlalchemy import select, update, func, and_
from sqlalchemy.exc import IntegrityError

from src.database.connection import session
from src.tables.models import Urls, UrlClicks
from src.tables.schemas import UrlStatistic


class UrlsService:
    """
    Сервис для работы с ссылками: создание, получение,
    деактивация и добавление кликов по ним
    """
    def __init__(self):
        """
        Инициализация сервиса с сессией базы данных

        Args:
            session: асинхронная сессия
        """
        self.session = session


    async def get_origin_url(self, short_url_key: str) -> Urls:
        """
        Получает оригинальную ссылку по ключу из короткого url

        Args:
            short_url_key(str): ключ короткой ссылки
        Returns:
            urls: объект таблицы Urls из базы данных
        """
        stmt = (
            select(Urls).filter(Urls.short_url.like(f'%/{short_url_key}'))
        )
        url = (await self.session.execute(stmt)).scalars().first()
        if not url:
            raise HTTPException(status_code=404, detail="Url not found")
        if not url.is_active:
            raise HTTPException(status_code=410, detail='Not active')
        return url


    async def deactivate_urls(self):
        """
        Деактивирует все ссылку, у которых истек срок действия
        """
        stmt = (
            update(Urls)
            .where(Urls.expires_at <= datetime.now(), Urls.is_active)
            .values(is_active=False)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return


    def _generate_prefix(self, origin_url: str) -> tuple[int, str]:
        """
       Генерирует префикс из первых трех частей ссылки

       Args:
           origin_url(str): оригинальный url

       Returns:
           tuple[int, List[str]]: кортеж, где первое значение -
           кол-во сегментов ссылки, а второе - список первых трех частей ссылки
           (например, ['http', '', 'localhost:8000'])
       """
        old_prefix = origin_url.split('/')
        prefix = 'http://localhost:8000'
        return (len(old_prefix), prefix)


    def _generate_key(self) -> str:
        """
        Генерирует случайный ключ из букв и цифр, по умолчанию длина 10

        Returns:
            str: сгенерированный ключ для короткой ссылки
        """
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for i in range(10))


    def _generate_short_url(self, origin_url: str) -> str:
        """
        Генерирует короткую ссылку, объединяя префикс и ключ
        Также проходит проверка является ли ссылка длиной(более 2 сегментов ссылки,
        если нет то не нужно фомировать короткую ссылку, так как она таковой уже
        является)

        Args:
            origin_url (str): оригинальный url

        Returns:
            str: короткий url
        """
        prefix = self._generate_prefix(origin_url)
        if prefix[0] <= 3:
            raise HTTPException(status_code=400, detail="To generate short url "
                                                        "must have at least 3 "
                                                        "path segments, like "
                                                        "'one://two/three'")
        key = self._generate_key()
        return prefix[1] + '/' + key


    async def add_url_click(self, short_url_key: str) -> UrlClicks:
        """
        Создает новую запись в таблице UrlClicks(id сслыки и время клика)
         о клике по ссылке

        Args:
            short_url_key(str): ключ короткой ссылки

        Returns:
            new_url(UrlClicks): запись в таблице UrlClicks
        """
        try:
            stmt = (
                select(Urls.id).filter(Urls.short_url.like(f'%/{short_url_key}'))
            )
            url_id = (await self.session.execute(stmt)).scalars().first()
            if not url_id:
                raise HTTPException(status_code=404, detail="Url not found")
            new_click = UrlClicks(
                url_id=url_id,
                clicked_at=datetime.now(),
            )
            self.session.add(new_click)
            await self.session.commit()
            return new_click
        except Exception:
            await self.session.rollback()
            raise


    async def create_new_url(self, origin_url: str, user_id: int) -> Urls:
        """
        Создает новую запись короткой ссылки в бд.
        Проверяет соотвествует ли она шаблону ссылки, т.е она вида http(https)://hi12 или
        http://localhost:8000 и т.д
        Если с первой попытки не удалось сформировать уникальную короткую ссылку,
        то будет произведено 10 попыток сформировать ее

        Args:
            origin_url(str): оригинальная ссылка
            user_id(int): id аутентифицированного пользователя, который создал ссылку

        Returns:
            Urls: объект таблицы Urls
        """
        regex = re.compile(
            r"^https?://"                                    
            r"("                                            
                r"localhost"                                 
                r"|"                                         
                r"(\d{1,3}\.){3}\d{1,3}"                     
                r"|"                                         
                r"([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}"           
            r")"
            r"(:\d+)?"                                      
            r"(/.*)?$"
        )
        if regex.match(origin_url):
            for attempt in range(10):
                try:
                    new_url = Urls(origin_url = origin_url,
                                  short_url = self._generate_short_url(origin_url),
                                  created_at = datetime.now(),
                                  expires_at = datetime.now() + timedelta(days=1),
                                  is_active = True,
                                  user_id = user_id)
                    self.session.add(new_url)
                    await self.session.commit()
                    return new_url
                except IntegrityError:
                    await self.session.rollback()
                    if attempt == 9:
                        raise Exception('Не удалось сгенерировать '
                                        'уникальную короткую ссылку '
                                        'за 10 попыток')
        else:
            raise HTTPException(status_code=400, detail="Incorrect original url, "
                                                        "must be like "
                                                        "'http(https)://hi12.com. "
                                                        "And it could have just "
                                                        "chars, digits, . and -'")


    async def get_short_urls(self, is_active: bool, limit: int,
                             offset: int) -> List[str]:
        """"
        Получает короткие ссылки из базы данных. Есть фильтрация и
        пагинация

        Args:
            - is_active: параметр фильтрации(False - получить все ссылки,
              True - только активные)
            - limit(int): количество ссылок для вывода
            - offset(int): с какой по порядку ссылки начинать вывод

        Returns:
            - urls_list(List[str]): список коротких ссылок
        """
        try:
            stmt = select(Urls.short_url)
            if is_active:
                stmt = stmt.where(Urls.is_active == is_active)

            stmt = stmt.limit(limit) if limit is not None else stmt
            stmt = stmt.offset(offset) if offset is not None else stmt

            result = await self.session.execute(stmt)
            urls = result.scalars().all()
            return urls
        except Exception:
            raise

urls_service = UrlsService()


class UrlsStatService:
    """
        Сервис для получения статистики по кликам на короткие url:
        за последний день и последний час

    """
    def __init__(self):
        """
        Инициализация сервиса с сессией базы данных

        Args:
            - session: асинхронная сессия
        """
        self.session = session
        self.timezone = pytz.timezone('Europe/Moscow')


    async def _get_last_hour_stat(self, short_url_id: str) -> int:
        """
        Подсчитывает количество кликов по короткой ссылке за последний час

        Args:
            - short_url_id(str): id короткой ссылки

        Returns:
            - int: количество кликов за последний час
        """
        now = datetime.now(self.timezone)
        one_hour_ago = now - timedelta(hours=1)
        one_hour_ago = one_hour_ago.replace(tzinfo=None)

        stmt = select(func.count()).where(
            and_(
            UrlClicks.url_id == short_url_id,
            UrlClicks.clicked_at >= one_hour_ago
            )
        )
        hour_stat = (await self.session.execute(stmt)).scalars().first()
        return hour_stat


    async def _get_last_day_stat(self, short_url_id: str) -> int:
        """
        Подсчитывает количество кликов по короткой ссылке за последний день

        Args:
            - short_url_id(str): id короткой ссылки

        Returns:
            - int: количество кликов за последний день
        """
        now = datetime.now(self.timezone)
        one_day_ago = now - timedelta(days=1)
        one_day_ago = one_day_ago.replace(tzinfo=None)

        stmt = select(func.count()).where(
            UrlClicks.url_id == short_url_id,
            UrlClicks.clicked_at >= one_day_ago
        )
        day_stat = (await self.session.execute(stmt)).scalars().first()
        return day_stat


    async def _get_all_short_urls(self) -> List[Urls]:
        """
        Получает список всех коротких url из базы данных

        Returns:
            - urls(List[str]): список коротких url
        """
        stmt = (select(Urls.short_url))
        urls = (await self.session.execute(stmt)).scalars().all()
        return urls


    async def get_full_stat(self) -> List[UrlStatistic]:
        """
        Формирует полную статистику по всем коротким url

        Для каждого короткого url получает объект Urls из базы,
        подсчитывает количество кликов за последний час и последний день,
        формирует объект UrlStatistic и собирает их в список.
        Список сортируется по количеству кликов за последний день в порядке убывания.

        Returns:
            - urls_stats(List[UrlStatistic]): отсортированный список статистики
                                              по коротким url
        """
        urls_stats = []
        short_urls = await self._get_all_short_urls()
        for short_url in short_urls:
            stmt = (select(Urls).where(Urls.short_url == short_url))
            url = (await self.session.execute(stmt)).scalars().first()
            if not url:
                raise HTTPException(status_code=404, detail="Url not found")
            hour_clicks = await self._get_last_hour_stat(url.id)
            day_clicks = await self._get_last_day_stat(url.id)
            statistic = UrlStatistic(
                link= url.short_url,
                orig_link= url.origin_url,
                last_hour_clicks= hour_clicks,
                last_day_clicks= day_clicks,
            )
            urls_stats.append(statistic)
        return sorted(urls_stats, key=lambda x: x.last_day_clicks, reverse=True)

urls_statistics_service = UrlsStatService()