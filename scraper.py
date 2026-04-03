import asyncio
import re
import logging
import httpx
import database

LOCATIONS = ["USA", "Mexico", "UK"]
NICHES = ["Real Estate", "Hospital", "Hotel", "Restaurant"]

SKIP_DOMAINS = [
    "duckduckgo.com", "google.com", "yelp.com", "wikipedia.org",
    "yellowpages.com", "facebook.com", "instagram.com", "linkedin.com",
    "tripadvisor.com", "booking.com", "hotels.com", "expedia.com",
    "yahoo.com", "hotmail.com", "zillow.com", "realtor.com"
]

EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+\-]+@(?:gmail|yahoo|hotmail|outlook)\.com', re.IGNORECASE)

async def fetch_page_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            return resp.text
    except Exception:
        return ""

def extract_emails(text: str):
    found = set(EMAIL_PATTERN.findall(text))
    # Filter obvious spam/template emails
    filtered = set()
    for e in found:
        lower = e.lower()
        if any(x in lower for x in ["noreply", "no-reply", "test@", "example", "user@", "email@", "name@"]):
            continue
        filtered.add(e)
    return filtered

async def ddgs_search(query: str, max_results: int = 20):
    """Run DuckDuckGo search synchronously in a thread to avoid blocking the event loop."""
    def _search():
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            logging.warning(f"DDGS search failed for query '{query}': {e}")
            return []
    return await asyncio.to_thread(_search)

async def process_results(results, niche, location):
    inserted_count = 0
    for r in results:
        url = r.get("href", "")
        snippet = r.get("body", "") + " " + r.get("title", "")

        if any(skip in url for skip in SKIP_DOMAINS):
            continue

        emails = extract_emails(snippet)

        if not emails and url.startswith("http"):
            page_text = await fetch_page_text(url)
            emails = extract_emails(page_text)

        for email in emails:
            name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
            inserted = await database.insert_lead(name=name, email=email, niche=niche, location=location)
            if inserted:
                logging.info(f"✅ New lead: {email} | {niche} | {location}")
                inserted_count += 1

    return inserted_count

async def scrape_new_leads():
    total = 0
    for location in LOCATIONS:
        for niche in NICHES:
            logging.info(f"🔍 Scraping: {niche} in {location}...")

            queries = [
                f'{niche} {location} contact "@gmail.com"',
                f'{niche} owner {location} email "@yahoo.com"',
                f'{niche} {location} gmail contact us',
            ]

            for query in queries:
                results = await ddgs_search(query, max_results=20)
                if results:
                    count = await process_results(results, niche, location)
                    total += count
                await asyncio.sleep(3)

    logging.info(f"Scraping complete. Total new leads found: {total}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(scrape_new_leads())
