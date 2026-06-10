from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import select

from app.models.news import News
from utils.logger import logger


DATABASE_URL = "sqlite+aiosqlite:///news.db"


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
        cutoff = datetime.utcnow() - timedelta(hours=48)
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
        news = News(title=title, text=text, source=source, url=url, created_at=str(datetime.utcnow()))
        session.add(news)
        await session.commit()
        await session.refresh(news)
        return {"ok": True, "news": news}
      except Exception as e:
        logger.error(f"add_news error: {e}")
        await session.rollback()
        raise