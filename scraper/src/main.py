import os
import time
import re
from datetime import datetime, timezone
import json
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError, HttpUrl
from typing import Optional
from urllib.parse import urljoin

CACHE_DIR = "cache"
OUTPUT_DIR = "output"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/TayyibaFatima/todo-api)"
TIMEOUT = 10
DELAY = 0.5


# ---------- Schema ----------

class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_gbp: float
    price_text: str
    availability_text: str
    rating_text: Optional[str] = None
    description: Optional[str] = None
    source_page: HttpUrl
    fetched_at: str


# ---------- Fetch (with retry) ----------

def fetch_page(url: str, cache_filename: str, retry: bool = True) -> tuple[str, bool]:
    """
    Fetch a page, using the cache if it exists.
    Returns (html, was_cache_hit). Raises RuntimeError on unrecoverable failure.
    """
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT: {cache_filename} ({len(html)} bytes)")
        return html, True

    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        if retry:
            print(f"TIMEOUT on {url}, retrying once...")
            time.sleep(1)
            return fetch_page(url, cache_filename, retry=False)
        raise RuntimeError(f"Timed out twice fetching {url}")

    response.encoding = "utf-8"

    if response.status_code in (404, 403):
        raise RuntimeError(f"Fetch refused for {url}: status {response.status_code}")

    if response.status_code >= 500 and retry:
        print(f"SERVER ERROR {response.status_code} on {url}, retrying once...")
        time.sleep(1)
        return fetch_page(url, cache_filename, retry=False)

    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch {url}: status {response.status_code}")

    html = response.text
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"FETCH: {cache_filename} ({len(html)} bytes)")
    time.sleep(DELAY)
    return html, False


# ---------- Stage 2: discovery ----------

def discover_catalogue_pages():
    base_url = "https://books.toscrape.com/catalogue/page-1.html"
    page_url = base_url
    page_num = 1
    all_book_urls = []
    cache_hits = 0

    while True:
        cache_filename = f"catalogue-page-{page_num}.html"
        html, was_cache_hit = fetch_page(page_url, cache_filename)
        if was_cache_hit:
            cache_hits += 1
        soup = BeautifulSoup(html, "html.parser")

        for h3 in soup.select("article.product_pod h3 a"):
            href = h3["href"]
            absolute_url = urljoin(page_url, href)
            all_book_urls.append(absolute_url)

        next_link = soup.select_one("li.next a")
        if not next_link or page_num >= 3:
            break

        next_href = next_link["href"]
        page_url = urljoin(page_url, next_href)
        page_num += 1

    unique_urls = list(dict.fromkeys(all_book_urls))
    print(f"catalogue_pages={page_num} discovered={len(all_book_urls)} unique_urls={len(unique_urls)}")
    return unique_urls, page_num, cache_hits


# ---------- Stage 3: extraction ----------

def safe_filename_from_url(url: str) -> str:
    slug = url.rstrip("/").split("/")[-2]
    return re.sub(r"[^a-zA-Z0-9_-]", "_", slug) + ".html"


def extract_book(book_url: str, source_page: str) -> tuple[Optional[dict], bool]:
    """Returns (record_or_none, was_cache_hit). record is None if the page failed."""
    cache_filename = safe_filename_from_url(book_url)

    try:
        html, was_cache_hit = fetch_page(book_url, cache_filename)
    except RuntimeError as e:
        print(f"FAILED PAGE: {book_url} ({e})")
        return None, False

    soup = BeautifulSoup(html, "html.parser")
    product_main = soup.select_one("div.product_main")
    title = product_main.select_one("h1").get_text(strip=True)
    price_text = product_main.select_one("p.price_color").get_text(strip=True)
    availability_text = product_main.select_one("p.availability").get_text(strip=True)

    rating_tag = product_main.select_one("p.star-rating")
    rating_text = None
    if rating_tag:
        classes = rating_tag.get("class", [])
        rating_text = next((c for c in classes if c != "star-rating"), None)

    desc_heading = soup.select_one("#product_description")
    if desc_heading:
        desc_p = desc_heading.find_next_sibling("p")
        description = desc_p.get_text(strip=True) if desc_p else None
    else:
        description = None

    record = {
        "title": title,
        "product_url": book_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    return record, was_cache_hit


# ---------- Stage 4: normalize + validate ----------

def normalize_price(price_text: str) -> float:
    cleaned = re.sub(r"[^\d.]", "", price_text)
    return float(cleaned)


def normalize_and_validate(raw_records: list[dict]):
    valid_records = []
    invalid_records = []
    seen_urls = set()

    for raw in raw_records:
        try:
            if raw["product_url"] in seen_urls:
                continue
            seen_urls.add(raw["product_url"])

            price_gbp = normalize_price(raw["price_text"])
            record_data = dict(raw)
            record_data["price_gbp"] = price_gbp

            validated = BookRecord(**record_data)
            valid_records.append(json.loads(validated.model_dump_json()))

        except (ValidationError, ValueError, KeyError) as e:
            invalid_records.append({"record": raw, "reason": str(e)})

    return valid_records, invalid_records


# ---------- Main ----------

if __name__ == "__main__":
    run_start = datetime.now(timezone.utc)

    book_urls, catalogue_pages_fetched, catalogue_cache_hits = discover_catalogue_pages()

    # Stage 5 proof: add one fake URL on purpose
    book_urls.append("https://books.toscrape.com/catalogue/this-book-does-not-exist_0000/index.html")

    raw_records = []
    failed_pages = 0
    detail_cache_hits = 0

    for url in book_urls:
        record, was_cache_hit = extract_book(url, source_page="https://books.toscrape.com/catalogue/page-1.html")
        if record is None:
            failed_pages += 1
            continue
        if was_cache_hit:
            detail_cache_hits += 1
        raw_records.append(record)

    print(f"detail_pages={len(raw_records)} failed_pages={failed_pages}")

    valid_records, invalid_records = normalize_and_validate(raw_records)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "books.json"), "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2, ensure_ascii=False)

    with open(os.path.join(OUTPUT_DIR, "errors.json"), "w", encoding="utf-8") as f:
        json.dump(invalid_records, f, indent=2, ensure_ascii=False)

    run_end = datetime.now(timezone.utc)

    run_report = {
        "start_time": run_start.isoformat(),
        "duration_seconds": (run_end - run_start).total_seconds(),
        "catalogue_pages_fetched": catalogue_pages_fetched,
        "cache_hits": catalogue_cache_hits + detail_cache_hits,
        "valid_records": len(valid_records),
        "invalid_records": len(invalid_records),
        "failed_pages": failed_pages,
    }
    with open(os.path.join(OUTPUT_DIR, "run-report.json"), "w", encoding="utf-8") as f:
        json.dump(run_report, f, indent=2)

    print(f"valid_records={len(valid_records)} invalid_records={len(invalid_records)} failed_pages={failed_pages}")