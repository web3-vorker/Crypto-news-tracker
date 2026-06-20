import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import select

from app.models.news import News
from app.models.strong_news import StrongNews
from utils.logger import logger


# На Render переменная DATABASE_URL приходит в виде
# postgres://user:pass@host/db — это старый формат, который не понимает
# asyncpg-драйвер, его нужно конвертировать в postgresql+asyncpg://...
# Локально, если переменная не задана, продолжаем работать на SQLite.
_raw_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///news.db")

if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgresql://") and "+asyncpg" not in _raw_url:
    _raw_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

DATABASE_URL = _raw_url


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)


async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_news() -> list[News]:
    async with async_session() as session:
      try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        result = await session.execute(
            select(News).where(News.created_at >= cutoff)
        )
        news_list = result.scalars().all()
        return news_list
      except Exception as e:
        logger.error(f"get_news error: {e}")
        raise
      

async def add_news(title: str, text: str, source: str, url: str) -> dict:
    async with async_session() as session:
      try:
        news = News(title=title, text=text, source=source, url=url)
        session.add(news)
        await session.commit()
        await session.refresh(news)
        return {"ok": True, "news": news}
      except Exception as e:
        logger.error(f"add_news error: {e}")
        await session.rollback()
        raise


async def add_strong_news(
    title: str,
    abridged_text: str,
    sentiment: str,
    score: int,
    reason: str,
    category: str,
    source: str,
    url: str
) -> dict:
    async with async_session() as session:
      try:
        news = StrongNews(
            title=title, 
            abridged_text=abridged_text, 
            sentiment=sentiment, 
            score=score, 
            reason=reason, 
            category=category, 
            source=source, 
            url=url,
        )
        session.add(news)
        await session.commit()
        await session.refresh(news)
        return {"ok": True, "news": news}
      except Exception as e:
        logger.error(f"add_strong_news error: {e}")
        await session.rollback()
        raise


async def get_strong_news() -> list[StrongNews]:
    async with async_session() as session:
      try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        result = await session.execute(
            select(StrongNews).where(StrongNews.created_at >= cutoff)
        )
        news_list = result.scalars().all()
        return news_list
      except Exception as e:
        logger.error(f"get_strong_news error: {e}")
        raise