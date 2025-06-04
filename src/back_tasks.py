from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.tables.urls import urls_service

scheduler = AsyncIOScheduler()

async def deactivate_urls_scheduled():
    """
    Запускает метод deactivate_urls экземпляра urls_service,
    так как если мы добавляли его напрямую в планировщик,
    то возникала бы ошибка(мы пытались бы добавить корутину,
    что не поддерживается планировщиком)
    """
    await urls_service.deactivate_urls()

scheduler.add_job(
    deactivate_urls_scheduled,
    trigger='interval',
    seconds=60,
    id='deactivate_urls',
    replace_existing=True
)