import aiohttp
import feedparser
from bs4 import BeautifulSoup
from app.collectors.base import BaseCollector
from app.config import TWITTER_ACCOUNTS, TWITTER_INSTANCES

from utils.logger import logger


class TwitterCollector(BaseCollector):
    
    async def fetch_rss(self, session, account):
        for instance in TWITTER_INSTANCES:
            try:
                url = f"{instance}/{account}/rss"
                async with session.get(url, timeout=8, allow_redirects=True) as response:
                    if response.status == 200:
                        return await response.text()
            except Exception:
                continue
        return None 
    

    async def fetch(self):
        news = []

        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            for account in TWITTER_ACCOUNTS:
                try:
                    rss_text = await self.fetch_rss(session, account)

                    if not rss_text:
                        logger.error(f"[TwitterCollector] все инстансы недоступны для @{account}")
                        continue

                    feed = feedparser.parse(rss_text)

                    for entry in feed.entries[:5]:
                        title = entry.title[:150]
                        
                        # пропускаем ретвиты
                        if title.startswith("RT by ") or title.startswith("R to "):
                            continue
                        
                        text = BeautifulSoup(
                            entry.get("summary", ""),
                            "html.parser"
                        ).get_text()

                        news.append({
                            "source": f"Twitter/@{account}",
                            "title": entry.title[:150],
                            "text": text,
                            "url": entry.link,
                        })

                except Exception as e:
                    logger.error(f"[TwitterCollector] @{account}: {e}")
                    continue

        return news