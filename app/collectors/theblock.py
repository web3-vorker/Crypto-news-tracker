import aiohttp
import feedparser

from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector


THEBLOCK_RSS = "https://www.theblock.co/rss.xml"


class TheBlockCollector(BaseCollector):

    async def fetch(self):

        async with aiohttp.ClientSession() as session:

            async with session.get(
                THEBLOCK_RSS,
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
                "source": "The Block",
                "title": entry.title,
                "text": summary,
                "url": entry.link,
                "published_at": entry.get("published", "")
            })

        return news