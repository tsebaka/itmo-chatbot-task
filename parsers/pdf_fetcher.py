from __future__ import annotations
from loguru import logger
from pathlib import Path
from typing import Iterable

import requests


def download_pdf(url: str, out_dir: str) -> Path:
    out = Path(out_dir)

    out.mkdir(parents=True, exist_ok=True)

    name = url.split("/")[-1].split("?")[0] or "document.pdf"

    path = out / name

    if path.exists() and path.stat().st_size > 0:
        return path

    r = requests.get(url, timeout=120)

    r.raise_for_status()

    path.write_bytes(r.content)

    logger.info("saved %s", path)

    return path


def download_many(urls: Iterable[str], out_dir: str) -> list[Path]:
    saved = []

    for u in urls:
        try:
            saved.append(download_pdf(u, out_dir))
        except Exception as e:
            logger.warning("fail %s: %s", u, e)
    return saved
