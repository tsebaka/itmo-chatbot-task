import threading
import uuid
from pathlib import Path
from typing import Any

import telebot
from telebot.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from loguru import logger

from config import (
    TELEGRAM_BOT_TOKEN,
    DOWNLOAD_DIR,
    START_URLS,
    REQUEST_TIMEOUT,
    USER_AGENT,
    SITE_MAX_PAGES,
    SITE_CONTEXT_LIMIT,
    MAX_FILES_PER_QUERY,
)

from gemini_client import GeminiClient
from parsers.pdf_fetcher import download_many
from parsers.site_parser import grab_text_and_pdfs


class TelegramBot:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini
        self.bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

        self.site_text_cache: str | None = None
        self.last_question_by_chat: dict[int, str] = {}
        self._file_registry: dict[str, str] = {}

        self._register_handlers()

    def _run_in_thread(self, fn, *args, **kwargs):
        t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
        t.start()
        return t

    def _list_local_pdfs(self) -> list[str]:
        base = Path(DOWNLOAD_DIR)
        if not base.exists():
            return []
        return [str(p) for p in base.rglob("*.pdf") if p.is_file()]

    @staticmethod
    def _filenames_from_paths(paths: list[str]) -> list[str]:
        return [Path(p).name for p in paths]

    def _mk_keyboard_for_candidates(
        self, candidates: list[str], all_paths: list[str]
    ) -> InlineKeyboardMarkup:
        kb = InlineKeyboardMarkup(row_width=1)

        matched = 0
        for name in candidates:
            match = next(
                (p for p in all_paths if Path(p).name.lower() == name.lower()), None
            )
            if not match:
                continue
            key = "use:" + uuid.uuid4().hex[:24]
            self._file_registry[key] = match
            kb.add(InlineKeyboardButton(
                text=f"Использовать: {name}", callback_data=key))
            matched += 1

        if matched == 0 and all_paths:
            for p in all_paths[:MAX_FILES_PER_QUERY]:
                key = "use:" + uuid.uuid4().hex[:24]
                self._file_registry[key] = p
                kb.add(
                    InlineKeyboardButton(
                        text=f"Использовать: {Path(p).name}", callback_data=key
                    )
                )

        kb.add(InlineKeyboardButton(
            text="Ответить без файла", callback_data="nofile"))
        return kb


    def _register_handlers(self):
        @self.bot.message_handler(commands=["start", "help"])
        def _start(msg: Message):
            self.bot.reply_to(
                msg,
                "Привет! Я помогу с вопросами по магистратурам ИТМО.\n\n"
                "Команды:\n"
                "/crawl_default — обойти сайт(ы), собрать текст и PDF (локально)\n"
                "/clear_index — очистить кэш\n\n"
                "Дальше просто задавайте вопрос — предложу релевантные PDF для апрува.",
            )

        @self.bot.message_handler(commands=["clear_index"])
        def _clear(msg: Message):
            self.site_text_cache = None
            self.last_question_by_chat.clear()
            self._file_registry.clear()
            self.bot.reply_to(msg, "Кэш очищен.")

        @self.bot.message_handler(commands=["crawl_default"])
        def _crawl_default(msg: Message):
            self.bot.reply_to(
                msg,
                "Стартую парсинг стартовых страниц... Это может занять несколько минут.",
            )

            def job():
                try:
                    text, pdfs = grab_text_and_pdfs(
                        START_URLS,
                        max_pages=SITE_MAX_PAGES,
                        timeout=REQUEST_TIMEOUT,
                        user_agent=USER_AGENT,
                        max_chars=SITE_CONTEXT_LIMIT,
                    )
                    self.site_text_cache = text

                    paths = download_many(pdfs, DOWNLOAD_DIR)

                    self.bot.send_message(
                        msg.chat.id,
                        "Готово.\n"
                        f"— Текст с сайта: {len(text)} символов\n"
                        f"— PDF найдено: {len(pdfs)}, скачано: {len(paths)}\n\n"
                        "Теперь задайте вопрос — предложу подходящие файлы для апрува.",
                    )
                except Exception as e:
                    logger.exception("Ошибка парсинга/скачивания")
                    self.bot.send_message(
                        msg.chat.id, f"Ошибка во время парсинга/скачивания: {e}"
                    )

            self._run_in_thread(job)

        @self.bot.message_handler(content_types=["text"])
        def _text(msg: Message):
            user_q = msg.text.strip()
            chat_id = msg.chat.id
            self.last_question_by_chat[chat_id] = user_q

            all_paths = self._list_local_pdfs()
            if not all_paths:
                prompt = (
                    "Ты отвечаешь на вопросы абитуриента по учебным программам ИТМО.\n"
                    "Ниже контекст, собранный с сайта. Если ответа нет в контексте — скажи об этом явно.\n\n"
                    f"{self.site_text_cache or ''}\n\n"
                    f"Вопрос: {user_q}"
                )
                try:
                    answer = self.gemini.generate_text(prompt)
                except Exception as e:
                    logger.exception("Gemini error")
                    self.bot.reply_to(msg, f"Gemini error: {e}")
                    return
                self.bot.reply_to(msg, answer or "Пустой ответ.")
                return

            filenames = self._filenames_from_paths(all_paths)
            try:
                candidates = self.gemini.select_filenames_via_llm(
                    question=user_q,
                    filenames=filenames,
                    k=MAX_FILES_PER_QUERY,
                    site_context=self.site_text_cache,
                )
            except Exception as e:
                logger.exception("Ошибка выбора файлов моделью")
                candidates = filenames[:MAX_FILES_PER_QUERY]

            # 3) Показываем варианты пользователю для апрува
            kb = self._mk_keyboard_for_candidates(candidates, all_paths)
            text = (
                "Нашёл подходящие файлы. Выберите, какой использовать для ответа.\n"
                "Или нажмите «Ответить без файла», чтобы ответить только по сайту."
            )
            self.bot.send_message(chat_id, text, reply_markup=kb)

        @self.bot.callback_query_handler(
            func=lambda call: call.data.startswith(
                "use:") or call.data == "nofile"
        )
        def _on_choose(call: CallbackQuery):
            chat_id = call.message.chat.id
            question = self.last_question_by_chat.get(chat_id, "").strip()
            if not question:
                self.bot.answer_callback_query(
                    call.id, "Не нашёл последний вопрос. Напишите заново."
                )
                return

            if call.data == "nofile":
                # Ответ только по сайту
                prompt = (
                    "Ты отвечаешь на вопросы абитуриента по учебным программам ИТМО.\n"
                    "Ниже контекст, собранный с сайта. Если ответа нет в контексте — скажи об этом явно.\n\n"
                    f"{self.site_text_cache or ''}\n\n"
                    f"Вопрос: {question}"
                )
                try:
                    answer = self.gemini.generate_text(prompt)
                except Exception as e:
                    logger.exception("Gemini error")
                    self.bot.send_message(chat_id, f"Gemini error: {e}")
                    return

                self.bot.send_message(chat_id, answer or "Пустой ответ.")
                self.bot.answer_callback_query(call.id, "Ответ без файла.")
                return

            key = call.data
            path = self._file_registry.get(key)
            if not path or not Path(path).exists():
                self.bot.answer_callback_query(call.id, "Файл не найден.")
                return

            self.bot.answer_callback_query(
                call.id, "Анализирую выбранный PDF...")

            try:
                answer = self.gemini.answer_with_pdf_path(
                    question=question,
                    pdf_path=path,
                    site_context=self.site_text_cache,
                    temperature=0.2,
                )
            except Exception as e:
                logger.exception("Ошибка анализа PDF")
                self.bot.send_message(chat_id, f"Ошибка анализа PDF: {e}")
                return

            self.bot.send_message(
                chat_id, f"Файл: {Path(path).name}\n\n{answer}")


    def run(self):
        logger.info("Запуск Telegram-бота (polling)...")
        self.bot.infinity_polling(
            skip_pending=True,
            allowed_updates=["message", "callback_query"],
        )
