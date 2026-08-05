import asyncio
import os
import time

import aiohttp
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.db.database import get_strong_news, get_strong_news_stats, engine
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


@app.get("/analytics")
async def get_analytics(
    hours: int = Query(72, ge=1, le=168),
    min_score: int = Query(0, ge=0, le=100),
    sentiment: str | None = Query(None, description="bullish|bearish|neutral"),
    category: str | None = Query(None),
) -> dict:
    analytics = await get_strong_news_stats(
        hours=hours,
        min_score=min_score,
        sentiment=sentiment,
        category=category,
    )
    return analytics


# ---------------------------------------------------------------------------
# Цены крипты (CoinGecko Demo API) с in-memory кэшем.
# Binance отдаёт 451 (geo-block) из дата-центра Render, поэтому используем
# CoinGecko с персональным Demo API-ключом — у нас отдельный от чужого
# трафика лимит (30 запросов/мин), не зависящий от шаринга IP на Render.
#
# Получить бесплатный ключ: https://www.coingecko.com/en/api/pricing -> Demo
# ---------------------------------------------------------------------------

from app.config import COINGECKO_API_KEY, COINGECKO_URL, COINGECKO_COINS, COINGECKO_CACHE_TTL

_price_cache: dict = {"data": None, "ts": 0}
CACHE_TTL_SECONDS = COINGECKO_CACHE_TTL


async def _fetch_prices_from_coingecko() -> list[dict]:
    params = {
        "vs_currency": "usd",
        "ids": ",".join(COINGECKO_COINS),
        "order": "market_cap_desc",
        "sparkline": "true",
        "price_change_percentage": "24h",
    }

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; CryptoNewsTracker/1.0)",
    }

    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY
    else:
        logger.warning(
            "get_prices: COINGECKO_API_KEY не задан — без ключа высок шанс "
            "упереться в общий рейт-лимит на шаренном IP Render"
        )

    max_attempts = 3

    async with aiohttp.ClientSession() as session:
        for attempt in range(1, max_attempts + 1):
            async with session.get(
                COINGECKO_URL, params=params, headers=headers, timeout=10
            ) as response:
                raw_text = await response.text()

                if response.status == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_s = int(retry_after) if retry_after else attempt * 5

                    logger.error(
                        f"get_prices: rate limited (attempt {attempt}/{max_attempts}), "
                        f"waiting {wait_s}s"
                    )

                    if attempt == max_attempts:
                        raise ValueError(f"CoinGecko status 429 after {max_attempts} attempts")

                    await asyncio.sleep(wait_s)
                    continue

                if response.status != 200:
                    logger.error(
                        f"get_prices: CoinGecko returned {response.status}: {raw_text[:300]}"
                    )
                    raise ValueError(f"CoinGecko status {response.status}")

                data = await response.json(content_type=None)

                if not isinstance(data, list):
                    logger.error(f"get_prices: unexpected response shape: {str(data)[:300]}")
                    raise ValueError("Unexpected CoinGecko response shape (not a list)")

                return [
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

    raise ValueError("get_prices: exhausted all retry attempts")


@app.get("/prices")
async def get_prices() -> list[dict]:
    now = time.time()

    if _price_cache["data"] is not None and (now - _price_cache["ts"]) < CACHE_TTL_SECONDS:
        return _price_cache["data"]

    try:
        result = await _fetch_prices_from_coingecko()

        _price_cache["data"] = result
        _price_cache["ts"] = now

        return result

    except Exception as e:
        logger.error(f"get_prices error: {e}")

        # При ошибке отдаём последний валидный кэш, если он есть, чтобы
        # дашборд не падал в пустоту на временных сбоях источника.
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