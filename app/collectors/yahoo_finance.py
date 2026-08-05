import aiohttp
import feedparser

from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector
from app.config import YAHOO_FINANCE_RSS


class YahooFinanceCollector(BaseCollector):

    RSS_URL = YAHOO_FINANCE_RSS

    async def fetch(self):

        async with aiohttp.ClientSession() as session:

            async with session.get(
                self.RSS_URL,
                timeout=10
            ) as response:

                rss_text = await response.text()

        feed = feedparser.parse(rss_text)

        news = []

        for entry in feed.entries[:15]:

            summary = BeautifulSoup(
                entry.get("summary", ""),
                "html.parser"
            ).get_text()

            news.append({
                "source": "Yahoo Finance",
                "title": entry.title,
                "text": summary,
                "url": entry.link,
            })

        return news