import asyncio
from rapidfuzz import fuzz
from app.collectors.coindesk import CoinDeskCollector
from app.collectors.cointelegraph import CointelegraphCollector
from app.collectors.theblock import TheBlockCollector
from app.collectors.cnbc_finance import CNBCFinanceCollector
from app.collectors.cnbc_world_news import CNBCWorldNewsCollector
from app.collectors.yahoo_finance import YahooFinanceCollector
from app.collectors.sec import SECCollector
from app.collectors.twitter import TwitterCollector

from app.db.database import (
  add_strong_news,
  engine, 
  get_news,
  add_news,
)

from app.ai.classifier import AI
from app.services.telegram import send_news
from app.models.base import Base
from utils.logger import logger


ai = AI()

async def create_tables():

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )


def is_duplicate(
    new_title: str,
    existing_titles: list[str],
    new_url: str,
    existing_urls: list[str]
) -> bool:

    for old_title in existing_titles:

        title_score = fuzz.token_set_ratio(
            new_title,
            old_title
        )

        if title_score > 85:
            return True

    for old_url in existing_urls:

        url_score = fuzz.token_set_ratio(
            new_url,
            old_url
        )

        if url_score > 95:
            return True

    return False


async def main():

    await create_tables()

    collectors = [
        CoinDeskCollector(),
        CointelegraphCollector(),
        TheBlockCollector(),
        SECCollector(),
        CNBCFinanceCollector(),
        CNBCWorldNewsCollector(),
        YahooFinanceCollector(),    
        TwitterCollector()
    ]

    KEYWORDS = [
    "bitcoin", "crypto", "fed", "inflation", "interest rate",
    "sec", "etf", "war", "sanctions", "tariffs", "china", "oil", "treasury",
    "iran", "russia", "strike", "attack", "military",
    "cpi", "gdp", "recession", "dollar", "debt",
    "israel", "ukraine", "nuclear", "missile",
    "trump", "congress", "white house",
    "rate", "economy", "market",
    ]

    BLACKLIST = [
    "price prediction",
    "what happened in crypto today",
    "opinion",
    "here's why",
    "explained",
    "guide",
    ]

    while True:
        
        news_history = await get_news()
        existing_titles = [n.title for n in news_history]
        existing_urls = [n.url for n in news_history]

        # Собираем новости со всех коллекторов без дубликатов
        batch = []

        total_collected = 0

        for collector in collectors:

            try:
                news_list = await collector.fetch()
                total_collected += len(news_list)


                for news in news_list:
                    if is_duplicate(news["title"], existing_titles, news["url"], existing_urls,):
                        logger.info(f"[DUPLICATE] {news['title']}")
                        continue

                    # Проверяем на наличие ключевых слов в заголовке и тексте
                    text = f"{news['title']} {news['text']}".lower()

                    if not any(keyword in text for keyword in KEYWORDS):
                        logger.info(f"[NOT IMPORTANT] {news['title']}")
                        continue

                    if any(black in text for black in BLACKLIST):
                        logger.info(f"[BLACKLISTED] {news['title']}")
                        continue

                    logger.info("=" * 50)
                    logger.info(news["source"])
                    logger.info(news["title"])
                    logger.info(news["url"])

                    batch.append({
                        "title": news["title"], 
                        "text": news["text"], 
                        "source": news["source"], 
                        "url": news["url"]
                    })

                    # Обновляем списки сразу, чтобы следующий коллектор не добавил дубль
                    existing_titles.append(news["title"])
                    existing_urls.append(news["url"])

                    # Сохраняем в базу
                    await add_news(
                        title=news["title"],
                        text=news["text"],
                        source=news["source"],
                        url=news["url"],
                    )

            except Exception as e:
                logger.error(f"[ERROR] {collector.__class__.__name__}: {e}")

  
        # Отправляем batch в AI для классификации и анализа
        results = []

        if batch:
            CHUNK_SIZE = 10

            for i in range(0, len(batch), CHUNK_SIZE):
                chunk = batch[i:i + CHUNK_SIZE]
                chunk_results = await ai.classify(chunk)
                results.extend(chunk_results)

            logger.info(f"[AI RESULTS] {results}")


        # Парсим результаты AI, отправляем в Telegram только сильные новости и сохраняем в отдельную таблицу StrongNews
        for result in results:
            if result["is_important"] and result["score"] > 70:
                logger.info(f"[STRONG NEWS] {result['title']} - {result['reason']}")

                await send_news(ai_result=result)

                # Сохраняем в таблицу StrongNews
                await add_strong_news(
                    title=result["title"],
                    abridged_text=result["abridged_text"],
                    sentiment=result["sentiment"],
                    score=result["score"],
                    reason=result["reason"],
                    category=result["category"],
                    source=result["source"],
                    url=result["url"]
                )

                    # TODO:
                    # ✅ Dedup
                    # ✅ AI analyze
                    # ✅ Telegram send
                    # ✅ Добавить новости по геополитике и макро-экономике

        # Логирование статистики
        logger.info(f"[CYCLE] Collected: {total_collected} | Passed filter: {len(batch)} | AI important: {len([r for r in results if r['is_important']])}")

        await asyncio.sleep(600)  # 10 минут


if __name__ == "__main__":
    asyncio.run(main())