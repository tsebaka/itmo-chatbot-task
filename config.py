import os

GOOGLE_API_KEY = os.getenv(
    "GOOGLE_API_KEY", "TOKEN_GEMINI"
)
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", "TOKEN_TG")

START_URLS = [
    "https://abit.itmo.ru/program/master/ai",
    "https://abit.itmo.ru/program/master/ai_product",
]

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")

MAX_PAGES = int(os.getenv("MAX_PAGES", "400"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
USER_AGENT = os.getenv("USER_AGENT", "itmo-2707-tgbot")
SITE_MAX_PAGES = int(os.getenv("SITE_MAX_PAGES", "400"))
SITE_CONTEXT_LIMIT = int(os.getenv("SITE_CONTEXT_LIMIT", "100000"))
MAX_FILES_PER_QUERY = int(os.getenv("MAX_FILES_PER_QUERY", "4"))
