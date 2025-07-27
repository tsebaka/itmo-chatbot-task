from __future__ import annotations

from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from loguru import logger


def grab_text_and_pdfs(
    start_urls: list[str],
    max_pages: int = 30,
    timeout: int = 15,
    user_agent: str = "itmo-2707-tgbot",
    max_chars: int | None = 100_000,
) -> tuple[str, list[str]]:
    headers = {"User-Agent": user_agent}
    visited: set[str] = set()

    queue: list[str] = list(dict.fromkeys(start_urls))

    roots = {urlparse(u).netloc for u in start_urls}

    def same_host(u: str) -> bool:
        host = urlparse(u).netloc
        return any(host == r or host.endswith("." + r) for r in roots)

    texts: list[str] = []
    pdfs: set[str] = set()

    logger.info("Старт парсинга: {} стартовых URL, лимит {} страниц",
                len(start_urls), max_pages)

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Пропускаю {}: {}", url, e)
            continue

        if "text/html" not in resp.headers.get("content-type", ""):
            logger.debug("Не HTML: {}", url)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        for t in soup(["script", "style", "noscript"]):
            t.extract()

        page_text = "\n".join(
            line.strip()
            for line in soup.get_text("\n").splitlines()
            if line.strip()
        )
        if page_text:
            texts.append(f"[{url}]\n{page_text}")

        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"]).split("#", 1)[0].strip()
            if not link.startswith("http"):
                continue

            path = link.split("?", 1)[0].lower()
            if path.endswith(".pdf"):
                if link not in pdfs:
                    pdfs.add(link)
                    logger.info("PDF: {}", link)
                continue

            if same_host(link) and link not in visited:
                queue.append(link)

    aggregated = "\n\n".join(texts)
    if max_chars is not None and len(aggregated) > max_chars:
        aggregated = aggregated[:max_chars]

    logger.success("Готово: страниц={}, pdfs={}, символов текста={}",
                   len(visited), len(pdfs), len(aggregated))
    return aggregated, sorted(pdfs)
