import aiohttp
import feedparser

from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector
from app.config import COINTELEGRAPH_RSS


class CointelegraphCollector(BaseCollector):

    async def fetch(self):

        async with aiohttp.ClientSession() as session:

            async with session.get(
                COINTELEGRAPH_RSS,
                timeout=10
            ) as response:

                rss_text = await response.text()

        feed = feedparser.parse(rss_text)

        news = []

        for entry in feed.entries[:15]:

            summary = BeautifulSoup(
                entry.get("summary", ""),
                "html.parser"
            ).get_text(" ", strip=True)

            news.append({
                "source": "Cointelegraph",
                "title": entry.title,
                "text": summary,
                "url": entry.link,
                "published_at": entry.get("published", "")
            })

        return news