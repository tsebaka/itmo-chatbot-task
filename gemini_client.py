from __future__ import annotations

from pathlib import Path
from typing import Optional, Any, List

from google import genai
from google.genai import types


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        cfg = types.GenerateContentConfig(temperature=temperature)
        if system_instruction:
            cfg.system_instruction = system_instruction
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=cfg,
        )
        return (getattr(resp, "text", "") or "").strip()

    def select_filenames_via_llm(
        self,
        question: str,
        filenames: List[str],
        k: int = 3,
        site_context: Optional[str] = None,
        temperature: float = 0.1,
    ) -> List[str]:
        if not filenames:
            return []

        catalog = "\n".join(filenames)
        parts: list[Any] = [
            "Сначала выбери до N названий файлов из списка ниже, наиболее релевантных вопросу.",
            "Верни строго JSON-массив строк (точные имена из списка). Если ни один не подходит — верни [].",
            f"N={max(1, k)}",
            f"Вопрос: {question}",
            "Список доступных файлов (по одному на строку):",
            catalog,
        ]
        if site_context:
            parts.insert(
                1, "Ниже есть краткий контекст сайта — используй его, чтобы понять, какие файлы выбрать.")

        resp = self.client.models.generate_content(
            model=self.model,
            contents=parts,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=list[str],
            ),
        )
        chosen = resp.parsed or []
        chosen_lower = {c.lower() for c in chosen if isinstance(c, str)}
        validated = [fn for fn in filenames if fn.lower() in chosen_lower]
        return validated[:max(1, k)]

    def answer_with_pdf_path(
        self,
        question: str,
        pdf_path: str,
        site_context: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        p = Path(pdf_path)
        if not p.exists():
            raise FileNotFoundError(pdf_path)

        pdf_part = types.Part.from_bytes(
            data=p.read_bytes(),
            mime_type="application/pdf",
        )

        contents: list[Any] = [pdf_part]
        instruction = (
            "Отвечай по содержимому документа. Если ответа нет в документе — скажи об этом явно."
        )
        if site_context:
            instruction = (
                "Ниже приложен документ. "
                "Также есть краткий контекст сайта; используй его только как фон.\n"
                "Если в документе нет ответа — скажи об этом явно."
            )
            contents.append(f"Контекст сайта (кратко):\n{site_context}")

        contents.append(instruction)
        contents.append(f"Вопрос: {question}")

        resp = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(temperature=temperature),
        )
        return (getattr(resp, "text", "") or "").strip()
