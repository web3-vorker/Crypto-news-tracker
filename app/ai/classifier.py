from openai import AsyncOpenAI, APIError, APIConnectionError
import json

from app.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODELS
from utils.logger import logger

class AI:
  """
  Модуль для классификации крипто-новостей с использованием OpenRouter API (OpenAI)
  """
  def __init__(self,):
    self.client = AsyncOpenAI(
      base_url=OPENROUTER_BASE_URL,
      api_key=OPENROUTER_API_KEY,
    )
    self.models = OPENROUTER_MODELS
    

  async def classify(self, batch: list[dict]) -> list[dict]:
    prompt_template = """
      Ты — AI-модуль для фильтрации крипто-новостей.

      Твоя задача:
      1. Определить, является ли новость важной для крипторынка.
      2. Оценить потенциальное влияние на рынок.
      3. Вернуть строго структурированный JSON без лишнего текста.

      НЕ придумывай факты. Используй только информацию из текста новости.
      НЕ делай длинных объяснений.
      НЕ пиши ничего кроме JSON.

      Проанализируй список новостей.

      Формат новостей: каждый элемент — это словарь с ключами "title", "text", "source", "url".
      Пример:

      [
        {
          "title": "Bitcoin surges after major company announces support",
          "text": "A major company has announced that it will start accepting Bitcoin as payment, causing the price of Bitcoin to surge by 15% in the last hour.",
          "source": "CoinDesk",
          "url": "https://www.coindesk.com/..."
        },
        ...
      ]

      Верни JSON-массив, где каждый элемент соответствует новости.

      Формат:

      [
        {
          "title": "...",
          "abridged_text": "...",  # краткое содержание новости (1-2 предложения)
          "url": "...",
          "source": "...",
          "is_important": true,
          "score": 0-100,
          "sentiment": "bullish|bearish|neutral",
          "category": "...",
          "affected_assets": ["..."],
          "reason": "..."
        }
      ]

      ОБЯЗАТЕЛЬНО ДОЛЖЕН БЫТЬ МАССИВ JSON

      Новости:

      NEWS_BATCH


      Правила:
      - is_important = true только если новость реально может повлиять на рынок
      - score = сила влияния на рынок (0 = мусор, 100 = сильный импакт)
      - sentiment — ожидаемое направление реакции рынка
      - category — краткая категория новости (например, regulation, etf, hack, partnership, market_movement и т.д.)
      - affected_assets — укажи активы, которые могут отреагировать (например, BTC, ETH, altcoins, DeFi, NFT и т.д.), только если уверен, иначе оставь пустым
      - reason — кратко и по делу (на русском), почему ты так оценил эту новость. Не пиши длинных текстов, только суть.

      - Возвращай название и краткое содержание новости на русском языке, даже если оригинал на английском или другом языке. Язык анализа — русский.

      
      Приоритеты оценки влияния на крипторынок:

      ВЫСОКИЙ SCORE (70-100) — события которые реально двигают рынок:
      - Военные конфликты, эскалации, удары (особенно США, Иран, Россия, Израиль)
      - Решения ФРС по ставкам, данные CPI/GDP/NFP
      - Санкции против крупных стран
      - Действия SEC, регуляторные решения по крипте
      - Крупные геополитические кризисы
      - Заявления Трампа про экономику, крипту, войны

      СРЕДНИЙ SCORE (40-69):
      - Макроэкономические данные (инфляция, безработица)
      - Политические события в США
      - Движения нефти, доллара, гособлигаций

      НИЗКИЙ SCORE (0-39) — шум который почти не влияет:
      - Кто-то купил или продал биткоины
      - Новый DeFi/NFT проект
      - Прогнозы и предсказания цены
      - Партнёрства мелких крипто-проектов
      - Технические обновления протоколов

      ВАЖНО: геополитика и макроэкономика влияют на крипту СИЛЬНЕЕ чем внутренние крипто-новости.
      BTC реагирует на войны и решения ФРС острее чем на новости внутри крипто-индустрии.
      """
    
    prompt = prompt_template.replace("NEWS_BATCH", json.dumps(batch, ensure_ascii=False, indent=2))

    for model in self.models:
      try: 
        response = await self.client.chat.completions.create(
          model=model,
          messages=[
            {"role": "user", "content": prompt}
          ],
          temperature=0.3
        )
        content = response.choices[0].message.content

        if not content:
            return []

        try:
            content = content.replace("```json", "")
            content = content.replace("```", "")
            content = content.strip()

            return json.loads(content)

        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"AI response content: {content}")

            return []
        
      except (APIError, APIConnectionError) as e:
        logger.error(f"AI API error: {e}")
        if "This model is unavailable" in str(e):
            logger.error(f"Model {model} is unavailable. Removing from list.")
            OPENROUTER_MODELS.remove(model)

        continue
      
    return []
  