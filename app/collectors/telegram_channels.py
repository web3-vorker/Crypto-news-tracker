from telethon import TelegramClient, events

CHANNELS = [
    "@wublockchain",
    "@coinness_en",
    "@forexlive_news",
    "@unusual_whales",
    "@marketsandmoney"
]

class TelegramCollector:
    def __init__(self, api_id, api_hash, session_name="news_session"):
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.buffer = []  # буфер новых сообщений

    async def start(self):
        await self.client.start()

        @self.client.on(events.NewMessage(chats=CHANNELS))
        async def handler(event):
            self.buffer.append({
                "source": f"Telegram/{event.chat.username}",
                "title": event.message.text[:100],  # первые 100 символов как заголовок
                "text": event.message.text,
                "url": f"https://t.me/{event.chat.username}/{event.message.id}",
            })

        await self.client.run_until_disconnected()

    async def fetch(self):
        messages = self.buffer.copy()
        self.buffer.clear()
        return messages