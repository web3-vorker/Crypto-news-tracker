import aiohttp
import feedparser

from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector
from app.config import SEC_RSS


class SECCollector(BaseCollector):

    RSS_URL = SEC_RSS

    async def fetch(self):

        async with aiohttp.ClientSession() as session:

            async with session.get(self.RSS_URL, timeout=10) as response:

                rss_text = await response.text()

        feed = feedparser.parse(rss_text)

        news = []

        for entry in feed.entries[:15]:

            summary = BeautifulSoup(
                entry.get("summary", ""),
                "html.parser"
            ).get_text()

            news.append({
                "source": "SEC Press Releases",
                "title": entry.title,
                "text": summary,
                "url": entry.link,
            })

        return news