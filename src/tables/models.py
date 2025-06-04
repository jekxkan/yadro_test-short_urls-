from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Urls(Base):
    """
    Модель ссылки, представляющая собой запись в таблице urls
    """
    __tablename__ = 'urls'

    id = Column(Integer, primary_key=True)
    origin_url = Column(String(1000))
    short_url = Column(String(100), unique=True)
    created_at = Column(DateTime)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer)
    clicks = relationship("UrlClicks", back_populates="url",
                          cascade="all, delete-orphan")

class UrlClicks(Base):
    """
    Модель статистики по короткой ссылке,
    представляющая собой запись в таблице url_clicks
    """
    __tablename__ = "url_clicks"

    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(Integer, ForeignKey("urls.id", ondelete="CASCADE"))
    clicked_at = Column(DateTime, default=datetime.utcnow, index=True)

    url = relationship("Urls", back_populates="clicks")

class Users(Base):
    """
    Модель пользователя, представляющая собой запись в таблице users
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    hashed_password = Column(String(300))