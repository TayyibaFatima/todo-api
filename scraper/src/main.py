import os
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

CACHE_DIR = "cache"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/TayyibaFatima/todo-api)"
TIMEOUT = 10
DELAY = 0.5


def fetch_page(url: str, cache_filename: str) -> str:
    """Fetch a page, using the cache if it already exists."""
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT: {cache_filename} ({len(html)} bytes)")
        return html

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)

    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch {url}: status {response.status_code}")

    html = response.text
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"FETCH: {cache_filename} ({len(html)} bytes)")
    time.sleep(DELAY)  # only matters when it was a real fetch, not a cache hit
    return html


def discover_catalogue_pages():
    """Follow 'next' links starting from page 1, up to 3 pages."""
    base_url = "https://books.toscrape.com/catalogue/page-1.html"
    page_url = base_url
    page_num = 1
    all_book_urls = []

    while True:
        cache_filename = f"catalogue-page-{page_num}.html"
        html = fetch_page(page_url, cache_filename)
        soup = BeautifulSoup(html, "html.parser")

        # collect book links on this page
        for h3 in soup.select("article.product_pod h3 a"):
            href = h3["href"]
            absolute_url = urljoin(page_url, href)
            all_book_urls.append(absolute_url)

        # find "next" link
        next_link = soup.select_one("li.next a")
        if not next_link or page_num >= 3:
            break

        next_href = next_link["href"]
        page_url = urljoin(page_url, next_href)
        page_num += 1

    unique_urls = list(dict.fromkeys(all_book_urls))  # dedupe, keep order

    print(f"catalogue_pages={page_num} discovered={len(all_book_urls)} unique_urls={len(unique_urls)}")
    return unique_urls


if __name__ == "__main__":
    urls = discover_catalogue_pages()