# itmo-chatbot-task

## 1. Make config.py

TELEGRAM_BOT_TOKEN = "ваш_токен_бота"

GOOGLE_API_KEY = "ваш_ключ_Gemini"

страницы для парсинга: START_URLS = ["https://example.com"] 

папка для сохранения PDF: DOWNLOAD_DIR = "data/downloads"       

лимит страниц: SITE_MAX_PAGES = 100                 

ограничение длины текста: SITE_CONTEXT_LIMIT = 100_000         

## 2. Start
python main.py

## 3. Instruction
- /crawl_default — бот обходит сайт, собирает текст и PDF

- Задайте вопрос — бот предложит подходящие PDF или ответит по тексту

- /clear_index — очистка кэша текста и списка PDF
