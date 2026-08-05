import asyncio
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import desc, select

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


async def get_news(hours: int = 48) -> list[News]:
    async with async_session() as session:
      try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await session.execute(
            select(News).where(News.created_at >= cutoff)
        )
        news_list = result.scalars().all()
        return news_list
      except Exception as e:
        logger.error(f"get_news error: {e}")
        raise


async def get_strong_news_stats(
    hours: int = 24,
    min_score: int = 0,
    sentiment: str | None = None,
    category: str | None = None,
) -> dict:
    async with async_session() as session:
      try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = select(StrongNews).where(StrongNews.created_at >= cutoff)

        if min_score:
          query = query.where(StrongNews.score >= min_score)
        if sentiment:
          query = query.where(StrongNews.sentiment == sentiment)
        if category:
          query = query.where(StrongNews.category == category)

        result = await session.execute(query)
        news_list = result.scalars().all()

        counts = {"bullish": 0, "bearish": 0, "neutral": 0}
        score_sums = {"bullish": 0, "bearish": 0, "neutral": 0}
        categories = {}
        sources = {}

        for news in news_list:
          sentiment_key = news.sentiment if news.sentiment in counts else "neutral"
          counts[sentiment_key] += 1
          score_sums[sentiment_key] += news.score or 0
          categories[news.category] = categories.get(news.category, 0) + 1
          sources[news.source] = sources.get(news.source, 0) + 1

        total_score = sum(score_sums.values())
        score_diff = score_sums["bullish"] - score_sums["bearish"]
        mood_index = round(score_diff / (total_score or 1), 3)

        if mood_index >= 0.15:
          mood = "bullish"
        elif mood_index <= -0.15:
          mood = "bearish"
        else:
          mood = "neutral"

        top_categories = [
            {"category": k, "count": v}
            for k, v in sorted(categories.items(), key=lambda item: item[1], reverse=True)
        ]
        top_sources = [
            {"source": k, "count": v}
            for k, v in sorted(sources.items(), key=lambda item: item[1], reverse=True)
        ]

        top_news = sorted(news_list, key=lambda n: n.score or 0, reverse=True)[:3]

        return {
          "hours": hours,
          "total": len(news_list),
          "counts": counts,
          "score_sums": score_sums,
          "mood": mood,
          "mood_index": mood_index,
          "top_categories": top_categories,
          "top_sources": top_sources,
          "top_news": [
            {
              "title": n.title,
              "score": n.score,
              "sentiment": n.sentiment,
              "category": n.category,
              "source": n.source,
              "url": n.url,
            }
            for n in top_news
          ],
        }
      except Exception as e:
        logger.error(f"get_strong_news_stats error: {e}")
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

