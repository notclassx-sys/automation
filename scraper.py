import asyncio
import re
import logging
import httpx
from duckduckgo_search import DDGS
import database

LOCATIONS = ["USA", "Mexico", "UK"]
NICHES = ["Real Estate", "Hospital", "Hotel", "Restaurant"]

# Domains to skip - these almost always HAVE websites
SKIP_DOMAINS = [
    "duckduckgo.com", "google.com", "yelp.com", "wikipedia.org",
    "yellowpages.com", "facebook.com", "instagram.com", "linkedin.com",
    "tripadvisor.com", "booking.com", "hotels.com", "expedia.com"
]

EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+\-]+@(?:gmail|yahoo|hotmail|outlook)\.com')

async def fetch_page_text(url: str) -> str:
    """Download a page and return its raw text to extract emails from."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            return resp.text
    except Exception:
        return ""

def extract_emails(text: str):
    return set(EMAIL_PATTERN.findall(text))

async def process_ddgs_results(results, niche, location):
    """Visit each result URL and scrape emails from the page body."""
    inserted_count = 0
    for r in results:
        url = r.get("href", "")
        snippet = r.get("body", "") + " " + r.get("title", "")
        
        # Skip known directory sites
        if any(skip in url for skip in SKIP_DOMAINS):
            continue

        # First try to get emails from snippet directly
        emails = extract_emails(snippet)

        # If no email in snippet, fetch the actual page
        if not emails and url:
            page_text = await fetch_page_text(url)
            emails = extract_emails(page_text)

        for email in emails:
            # Skip generic / spam emails
            if any(x in email for x in ["noreply", "no-reply", "support", "info@gmail", "test@"]):
                continue
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
            
            # Multiple search queries to maximise hit rate
            queries = [
                f'{niche} {location} contact "@gmail.com" OR "@yahoo.com"',
                f'{niche} owner {location} email "@gmail.com"',
                f'"{niche}" "{location}" "no website" "@gmail.com"',
            ]
            
            for query in queries:
                try:
                    results = DDGS().text(query, max_results=20)
                    if results:
                        count = await process_ddgs_results(results, niche, location)
                        total += count
                except Exception as e:
                    logging.error(f"DDGS Error: {e}")
                
                await asyncio.sleep(2)  # Rate limit between queries
                
    logging.info(f"Scraping complete. Total new leads found: {total}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(scrape_new_leads())
