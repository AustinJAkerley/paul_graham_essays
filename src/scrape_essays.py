"""Scrape Paul Graham's essays from paulgraham.com.

Fetches the essay index, then downloads and extracts the plain text of each
essay into the local ``essays/`` directory (one ``.txt`` file per essay).

The essays are Copyright (c) Paul Graham. This tool downloads them for
personal use (e.g. listening to them as audio). Do not redistribute the
text or generated audio without permission.
"""

from __future__ import annotations

import argparse
import os
import re
import time
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://www.paulgraham.com/"
INDEX_URL = urljoin(BASE_URL, "articles.html")

# Index links that are not essays and should be skipped.
SKIP_HREFS = {
    "index.html",
    "articles.html",
    "rss.html",
    "books.html",
    "faq.html",
}

USER_AGENT = (
    "Mozilla/5.0 (compatible; pg-essays-tts/1.0; personal archival use)"
)

# Minimum length (chars) of extracted text to treat a page as a real essay.
MIN_ESSAY_LENGTH = 200


@dataclass
class Essay:
    """A single essay: its title, source URL and local slug."""

    title: str
    url: str
    slug: str


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def slugify(value: str) -> str:
    """Turn a title or filename into a safe, stable file slug."""

    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value)
    return value.strip("-") or "essay"


def fetch_essay_index(session: requests.Session) -> list[Essay]:
    """Return the list of essays linked from the articles index page."""

    resp = session.get(INDEX_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    essays: list[Essay] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if not href.endswith(".html"):
            continue
        if "/" in href or ":" in href:
            # Only follow relative links that live on paulgraham.com itself.
            continue
        if href in SKIP_HREFS or href in seen:
            continue
        title = link.get_text(strip=True)
        if not title:
            continue
        seen.add(href)
        essays.append(
            Essay(title=title, url=urljoin(BASE_URL, href), slug=slugify(href[:-5]))
        )
    return essays


def extract_essay_text(html: str) -> str:
    """Extract the readable body text of an essay page.

    Paul Graham's pages are minimal HTML. The essay body is the largest
    block of text on the page, so we collect text from the document and
    normalise whitespace and line breaks.
    """

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    # The main body of a PG essay is rendered inside a <font> element.
    # Pick the one with the most text; fall back to the whole document.
    candidates = soup.find_all("font")
    node = max(candidates, key=lambda t: len(t.get_text()), default=None)
    if node is None or len(node.get_text(strip=True)) < MIN_ESSAY_LENGTH:
        node = soup.body or soup

    text = node.get_text("\n")
    # Collapse runs of blank lines and trailing spaces.
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def download_essays(
    out_dir: str = "essays",
    delay: float = 1.0,
    limit: int | None = None,
    overwrite: bool = False,
) -> list[Essay]:
    """Download all essays to ``out_dir``. Returns the essays processed."""

    os.makedirs(out_dir, exist_ok=True)
    session = _session()
    essays = fetch_essay_index(session)
    if limit is not None:
        essays = essays[:limit]

    print(f"Found {len(essays)} essays.")
    for i, essay in enumerate(essays, start=1):
        path = os.path.join(out_dir, f"{essay.slug}.txt")
        if os.path.exists(path) and not overwrite:
            print(f"[{i}/{len(essays)}] skip (exists): {essay.slug}")
            continue
        try:
            resp = session.get(essay.url, timeout=30)
            resp.raise_for_status()
            # PG pages are usually latin-1/ascii; let requests guess sensibly.
            resp.encoding = resp.apparent_encoding or resp.encoding
            text = extract_essay_text(resp.text)
        except requests.RequestException as exc:  # network / HTTP errors
            print(f"[{i}/{len(essays)}] ERROR {essay.slug}: {exc}")
            continue

        if len(text) < MIN_ESSAY_LENGTH:
            print(f"[{i}/{len(essays)}] WARN short/empty, skipping: {essay.slug}")
            continue

        header = f"{essay.title}\n\n"
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(header + text + "\n")
        print(f"[{i}/{len(essays)}] saved: {essay.slug} ({len(text)} chars)")
        time.sleep(delay)

    return essays


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Paul Graham essays as text.")
    parser.add_argument("--out", default="essays", help="Output directory.")
    parser.add_argument(
        "--delay", type=float, default=1.0, help="Seconds to wait between requests."
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Only download the first N essays."
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Re-download essays that already exist."
    )
    args = parser.parse_args()
    download_essays(
        out_dir=args.out, delay=args.delay, limit=args.limit, overwrite=args.overwrite
    )


if __name__ == "__main__":
    main()
