import os
import time

import aiohttp
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.db.database import get_strong_news, engine
from app.models.base import Base
from utils.logger import logger


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    # create_all идемпотентен (CREATE TABLE IF NOT EXISTS), поэтому безопасно
    # вызывать его и здесь, и в воркере — независимо от того, что стартует раньше.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/news")
async def get_news(
    limit: int = Query(100, ge=1, le=500),
    min_score: int = Query(0, ge=0, le=100),
    sentiment: str | None = Query(None, description="bullish|bearish|neutral"),
    category: str | None = Query(None),
) -> list[dict]:
    strong_news = await get_strong_news()

    # Свежие сначала
    strong_news = sorted(strong_news, key=lambda n: n.created_at, reverse=True)

    result = []
    for news in strong_news:
        if news.score < min_score:
            continue
        if sentiment and news.sentiment != sentiment:
            continue
        if category and news.category != category:
            continue

        result.append({
            "title": news.title,
            "abridged_text": news.abridged_text,
            "url": news.url,
            "source": news.source,
            "score": news.score,
            "sentiment": news.sentiment,
            "category": news.category,
            "reason": news.reason,
            "created_at": news.created_at.isoformat() if news.created_at else None,
        })

        if len(result) >= limit:
            break

    return result


# ---------------------------------------------------------------------------
# Цены крипты (CoinGecko) с простым in-memory кэшем, чтобы не упираться
# в рейт-лимиты публичного API при частом опросе дашбордом.
# ---------------------------------------------------------------------------

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINS = ["bitcoin", "ethereum", "dogecoin"]

_price_cache: dict = {"data": None, "ts": 0}
CACHE_TTL_SECONDS = 60


@app.get("/prices")
async def get_prices() -> list[dict]:
    now = time.time()

    if _price_cache["data"] is not None and (now - _price_cache["ts"]) < CACHE_TTL_SECONDS:
        return _price_cache["data"]

    params = {
        "vs_currency": "usd",
        "ids": ",".join(COINS),
        "order": "market_cap_desc",
        "sparkline": "true",
        "price_change_percentage": "24h",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(COINGECKO_URL, params=params, timeout=10) as response:
                data = await response.json()

        result = [
            {
                "id": coin["id"],
                "symbol": coin["symbol"].upper(),
                "name": coin["name"],
                "price": coin["current_price"],
                "change_24h": coin.get("price_change_percentage_24h"),
                "sparkline": coin.get("sparkline_in_7d", {}).get("price", []),
            }
            for coin in data
        ]

        _price_cache["data"] = result
        _price_cache["ts"] = now

        return result

    except Exception as e:
        logger.error(f"get_prices error: {e}")

        # При ошибке отдаём последний валидный кэш, если он есть, чтобы
        # дашборд не падал в пустоту на временных сбоях CoinGecko.
        if _price_cache["data"] is not None:
            return _price_cache["data"]

        return []


# ---------------------------------------------------------------------------
# Превью-картинка статьи (og:image), как делает Telegram link preview.
# Кэшируем по url, т.к. это медленный запрос и дёргать его на каждую
# карточку в ленте смысла нет — только когда юзер раскрывает новость.
# ---------------------------------------------------------------------------

_preview_cache: dict = {}
PREVIEW_CACHE_MAX = 500


@app.get("/preview")
async def get_preview(url: str = Query(...)) -> dict:
    if url in _preview_cache:
        return _preview_cache[url]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    result = {"image": None}

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=8, allow_redirects=True) as response:
                html = await response.text()

        og_image = _extract_og_image(html)
        result = {"image": og_image}

    except Exception as e:
        logger.debug(f"get_preview failed for {url}: {e}")

    # простой ограниченный кэш, чтобы не расти бесконечно
    if len(_preview_cache) >= PREVIEW_CACHE_MAX:
        _preview_cache.pop(next(iter(_preview_cache)))

    _preview_cache[url] = result
    return result


def _extract_og_image(html: str) -> str | None:
    import re

    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.api.api:app", host="0.0.0.0", port=port)