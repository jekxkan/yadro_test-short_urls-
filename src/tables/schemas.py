from datetime import datetime

from pydantic import BaseModel


class UrlStatistic(BaseModel):
    """
    Pydantic-модель объекта статистики для коротких url
    """
    link: str
    orig_link: str
    last_hour_clicks: int
    last_day_clicks: int

class Url(BaseModel):
    """
    Pydantic-модель объекта короткого url
    """
    origin_url: str
    short_url: str
    created_at: datetime
    expires_at: datetime
    is_active: bool
    user_id: int