"""
ingest.py — Stage 1 of the RAG pipeline: Document Ingestion.

Fetches raw text from each source in sources.py and stores it under documents/
as a UTF-8 .txt file, plus a manifest.json recording per-document metadata
(source name, url, type, official flag, fetch time, char count).

Design notes tied to planning.md:
  * Metadata (source + fetch date + official flag) is captured here so the
    chunking/embedding stages can attach it to every chunk. This is the
    mitigation for "outdated or conflicting immigration information": answers
    can cite their source and prefer official (USCIS/DHS) text.
  * Reddit pages can't be scraped as plain HTML, so reddit-type sources are
    pulled from the public .json listing endpoint instead.
  * Ingestion never crashes the whole run on one bad source — each failure is
    recorded in the manifest so you can see exactly which sources loaded.

Usage:
    python ingest.py
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from sources import SOURCES

load_dotenv()  # read REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET from .env if present

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

DOCUMENTS_DIR = Path(__file__).parent / "documents"
MANIFEST_PATH = DOCUMENTS_DIR / "manifest.json"

# Drop a hand-saved "{id}.txt" here for any source that can't be fetched
# automatically (e.g. Reddit when you don't have API credentials). It will be
# picked up as a fallback and recorded in the manifest with status "manual".
MANUAL_DIR = DOCUMENTS_DIR / "manual"

# A real browser User-Agent. Many sites (and Reddit) reject the default
# python-requests UA with 403/429.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 20  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds, multiplied by attempt number

# Reddit: how many posts to pull and the minimum body length worth keeping.
REDDIT_POST_LIMIT = 40
REDDIT_MIN_SELFTEXT = 80  # chars; skip link-only / one-line posts
# Reddit requires a unique, descriptive UA for its API (browser UAs get 403'd).
REDDIT_UA = "guide-ingest/0.1 by international-student-rag"

# HTML tags whose text is navigation/boilerplate, not content.
_BOILERPLATE_TAGS = ["script", "style", "nav", "header", "footer", "aside",
                     "form", "noscript", "svg", "button"]


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #

def fetch(url: str, *, as_json: bool = False):
    """GET a URL with retries and a browser UA. Returns response text or dict."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json() if as_json else resp.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)
    raise last_error  # exhausted retries


# --------------------------------------------------------------------------- #
# Text extraction
# --------------------------------------------------------------------------- #

def _collapse_whitespace(text: str) -> str:
    """Normalize whitespace: collapse runs of spaces, cap blank lines at one."""
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    out, blank = [], False
    for ln in lines:
        if ln:
            out.append(ln)
            blank = False
        elif not blank:
            out.append("")  # keep a single blank line as a paragraph break
            blank = True
    return "\n".join(out).strip()


def extract_html_text(html: str) -> str:
    """Pull the main readable text out of an HTML page.

    Strips scripts/nav/footers, prefers <main>/<article> if present, and keeps
    headings, paragraphs, and list items so semantic chunking (Stage 2) has
    section boundaries to work with.
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(_BOILERPLATE_TAGS):
        tag.decompose()

    # Prefer the main content region when the page marks one.
    root = soup.find("main") or soup.find("article") or soup.body or soup

    blocks: list[str] = []
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = el.get_text(separator=" ", strip=True)
        if not text:
            continue
        if el.name in ("h1", "h2", "h3", "h4"):
            blocks.append("\n" + text)  # blank line before a heading
        elif el.name == "li":
            blocks.append("- " + text)
        else:
            blocks.append(text)

    # Fallback: if the page used non-standard markup and we found nothing,
    # take the whole visible text rather than returning empty.
    if not blocks:
        blocks = [root.get_text(separator="\n", strip=True)]

    return _collapse_whitespace("\n".join(blocks))


def _reddit_token() -> str | None:
    """Get a read-only Reddit OAuth token via the client_credentials grant.

    Returns None if no credentials are configured. Register a free app (type
    "script") at https://www.reddit.com/prefs/apps to get a client id/secret,
    then put them in .env as REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET.
    """
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    if not (client_id and client_secret):
        return None
    resp = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": REDDIT_UA},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def extract_reddit_text(url: str) -> str:
    """Fetch a subreddit's recent posts via Reddit's authenticated API.

    Reddit blocks anonymous .json access with a 403, so this requires API
    credentials in .env (see _reddit_token). Each kept post becomes a small
    section: title + body — turning a live forum into static text the rest of
    the pipeline can treat like any other document.
    """
    token = _reddit_token()
    if not token:
        raise RuntimeError(
            "Reddit requires API credentials. Set REDDIT_CLIENT_ID and "
            "REDDIT_CLIENT_SECRET in .env (free app at "
            "https://www.reddit.com/prefs/apps), or save the thread text to "
            f"documents/manual/ as a .txt file."
        )

    subreddit = url.rstrip("/").split("/r/")[-1]
    api_url = f"https://oauth.reddit.com/r/{subreddit}/hot?limit={REDDIT_POST_LIMIT}"
    resp = requests.get(
        api_url,
        headers={"Authorization": f"bearer {token}", "User-Agent": REDDIT_UA},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    posts = data.get("data", {}).get("children", [])
    sections: list[str] = []
    for child in posts:
        post = child.get("data", {})
        if post.get("stickied"):
            continue
        title = (post.get("title") or "").strip()
        body = (post.get("selftext") or "").strip()
        if not title or len(body) < REDDIT_MIN_SELFTEXT:
            continue
        sections.append(f"\n{title}\n{body}")

    return _collapse_whitespace("\n".join(sections))


# --------------------------------------------------------------------------- #
# Per-source ingestion
# --------------------------------------------------------------------------- #

def ingest_source(source: dict) -> dict:
    """Fetch + extract one source. Returns a manifest record (success or error)."""
    record = {
        "id": source["id"],
        "name": source["name"],
        "url": source["url"],
        "type": source["type"],
        "official": source["official"],
        "description": source["description"],
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    fetch_status = "ok"
    try:
        if source["type"] == "reddit":
            text = extract_reddit_text(source["url"])
        else:
            text = extract_html_text(fetch(source["url"]))

        if not text or len(text) < 200:
            raise ValueError(
                f"extracted text too short ({len(text)} chars) — likely blocked "
                f"or empty page"
            )
    except Exception as exc:  # noqa: BLE001 — try the manual fallback next
        manual_path = MANUAL_DIR / f"{source['id']}.txt"
        if manual_path.exists() and len(manual_path.read_text(encoding="utf-8")) >= 200:
            text = manual_path.read_text(encoding="utf-8").strip()
            fetch_status = "manual"
        else:
            record.update(status="error", error=f"{type(exc).__name__}: {exc}")
            return record

    try:
        out_path = DOCUMENTS_DIR / f"{source['id']}.txt"
        header = (
            f"SOURCE: {source['name']}\n"
            f"URL: {source['url']}\n"
            f"OFFICIAL: {source['official']}\n"
            f"FETCHED_AT: {record['fetched_at']}\n"
            f"{'=' * 70}\n\n"
        )
        out_path.write_text(header + text, encoding="utf-8")

        record.update(
            status=fetch_status,
            file=out_path.name,
            char_count=len(text),
            word_count=len(text.split()),
        )
    except Exception as exc:  # noqa: BLE001 — record any failure, keep going
        record.update(status="error", error=f"{type(exc).__name__}: {exc}")

    return record


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def main() -> None:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Ingesting {len(SOURCES)} sources into {DOCUMENTS_DIR}\n")
    manifest = []
    for source in SOURCES:
        print(f"  [{source['id']}] {source['name']} ... ", end="", flush=True)
        record = ingest_source(source)
        manifest.append(record)
        if record["status"] in ("ok", "manual"):
            tag = "" if record["status"] == "ok" else " [manual]"
            print(f"ok ({record['char_count']:,} chars){tag}")
        else:
            print(f"FAILED — {record['error']}")

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    ok = [r for r in manifest if r["status"] in ("ok", "manual")]
    failed = [r for r in manifest if r["status"] == "error"]
    total_chars = sum(r["char_count"] for r in ok)

    print(f"\nDone: {len(ok)}/{len(SOURCES)} sources ingested, "
          f"{total_chars:,} total chars.")
    print(f"Manifest written to {MANIFEST_PATH}")
    if failed:
        print("\nFailed sources (re-run, or add the text manually to documents/):")
        for r in failed:
            print(f"  - {r['name']}: {r['error']}")


if __name__ == "__main__":
    main()
