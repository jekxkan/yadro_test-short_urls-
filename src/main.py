from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from src.back_tasks import scheduler
from src.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управляет жизненным циклом приложения

    При старте запускает планировщик задач для выполнения
    фоновых задач(например, автоматическая деактивация просроченных коротких ссылок)

    После завершения работы останавливает планировщик
    """
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)