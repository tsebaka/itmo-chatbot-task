from utils.logger import setup_logging
from config import GOOGLE_API_KEY
from gemini_client import GeminiClient
from telegram_bot import TelegramBot
from loguru import logger


def main():
    logger = setup_logging(log_file="logs/bot.log")
    logger.info("Starting tg-bot...")
    gemini = GeminiClient(api_key=GOOGLE_API_KEY, model="gemini-2.5-flash")
    TelegramBot(gemini).run()


if __name__ == "__main__":
    main()
