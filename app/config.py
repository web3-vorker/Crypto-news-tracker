import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://api.groq.com/openai/v1")
OPENROUTER_MODELS = [model.strip() for model in os.getenv("GROQ_MODELS", "").split(",") if model.strip()]

COINGECKO_URL = os.getenv("COINGECKO_URL", "https://api.coingecko.com/api/v3/coins/markets")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")
COINGECKO_COINS = [coin.strip() for coin in os.getenv("COINGECKO_COINS", "bitcoin,ethereum,dogecoin").split(",") if coin.strip()]
COINGECKO_CACHE_TTL = int(os.getenv("COINGECKO_CACHE_TTL", "60"))

COINDESK_RSS = os.getenv("COINDESK_RSS", "https://www.coindesk.com/arc/outboundfeeds/rss/")
COINTELEGRAPH_RSS = os.getenv("COINTELEGRAPH_RSS", "https://cointelegraph.com/rss")
THEBLOCK_RSS = os.getenv("THEBLOCK_RSS", "https://www.theblock.co/rss.xml")
CNBC_FINANCE_RSS = os.getenv("CNBC_FINANCE_RSS", "https://www.cnbc.com/id/100003114/device/rss/rss.html")
CNBC_WORLD_RSS = os.getenv("CNBC_WORLD_RSS", "https://www.cnbc.com/id/100727362/device/rss/rss.html")
SEC_RSS = os.getenv("SEC_RSS", "https://www.sec.gov/rss/pressrelease.xml")
YAHOO_FINANCE_RSS = os.getenv("YAHOO_FINANCE_RSS", "https://finance.yahoo.com/news/rssindex")

TWITTER_INSTANCES = [
    instance.strip()
    for instance in os.getenv(
        "TWITTER_INSTANCES",
        "https://rss.xcancel.com,https://nitter.net,https://nitter.catsarch.com,https://nitter.tiekoetter.com,https://nitter.kareem.one,https://nitter.42l.fr,https://nitter.space,https://lightbrd.com,https://nitter.privacyredirect.com,https://nuku.trabun.org,https://nitter.privacyredirect.com,https://nitter.net,https://nitter.poast.org"
    ).split(",")
    if instance.strip()
]

TWITTER_ACCOUNTS = [
    account.strip()
    for account in os.getenv(
        "TWITTER_ACCOUNTS",
        "Reuters,AP,BBCBreaking,AJEnglish,FedReserve,@SecScottBessent,WSJmarkets,markets,OSINTdefender,WarMonitor3,LizAnnSonders,RaoulGMI,zerohedge,realDonaldTrump,POTUS"
    ).split(",")
    if account.strip()
]
