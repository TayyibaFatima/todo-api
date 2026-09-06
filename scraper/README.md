Books to Scrape — Polite Scraper (Assignment)



Target classification



\- Site: https://books.toscrape.com

\- Why it's OK to scrape:\*\* The parent site (toscrape.com) explicitly describes itself as a sandbox built for people to practice web scraping on. No real business or personal data is involved.

\- Scope: Only the first 3 catalogue pages, and the \~60 book detail pages linked from them. No other pages or sites are touched.

\- Data collected: Book title, price, availability, star rating, description, and page URLs — all publicly displayed on the page for anyone visiting.

\- robots.txt result: no robots file found

\- Note: I will not reuse this code on another site without checking its rules and terms first.



How to run



1\. Clone this repo and `cd scraper`

2\. Create a venv and activate it:

python -m venv venv

venv\\Scripts\\activate.bat

3\. Install dependencies:

pip install requests beautifulsoup4 pydantic

4\. Run the scraper:

python src\\main.py

5\. Output appears in `output/books.json`, `output/errors.json`, and `output/run-report.json`



Lane



Python — Requests for HTTP, BeautifulSoup for parsing, Pydantic for schema validation.



Record schema



Each record in `books.json` has: `title`, `product\_url`, `price\_gbp`, `price\_text`, `availability\_text`, `rating\_text`, `description` (nullable), `source\_page`, `fetched\_at`.



Politeness rules



\- Identifying User-Agent on every request: `FlyRankInternshipA9/1.0 (+link)`

\- 10-second timeout per request

\- 0.5-second delay between real (non-cached) requests

\- Status code checked before parsing; 404/403 are not retried, 5xx and timeouts get one retry

\- All pages cached to `cache/` after first fetch — reruns during development hit the cache, not the live site



Sample run report



{

&#x20; "start\_time": "2026-09-06T18:33:28.556667+00:00",

&#x20; "duration\_seconds": 8.184743,

&#x20; "catalogue\_pages\_fetched": 3,

&#x20; "cache\_hits": 63,

&#x20; "valid\_records": 60,

&#x20; "invalid\_records": 0,

&#x20; "failed\_pages": 1

}



Why no browser was needed



All the book data (title, price, availability, description) is present directly in the HTML the server sends back — nothing is loaded afterward by JavaScript. A browser would only add cost (memory, startup time) with no benefit here.



Known limitation



Retries only happen once (not with exponential backoff), and the scraper doesn't yet detect which records changed between runs — a rerun overwrites `books.json` with a fresh copy rather than diffing against the previous one.



Ethics note



This scraper only touches a public sandbox built for practicing scraping. In real projects: check for an official API first, never bypass logins/paywalls/blocks, and collect only the data actually needed.



