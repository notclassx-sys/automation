import asyncio
import re
import logging
import httpx
import database

LOCATIONS = ["USA", "Mexico", "UK", "Canada", "Australia"]
NICHES = ["Real Estate", "Hospital", "Hotel", "Restaurant", "Cleaning Service", "Plumber", "Auto Repair"]

SKIP_DOMAINS = [
    "duckduckgo.com", "google.com", "yelp.com", "wikipedia.org",
    "yellowpages.com", "facebook.com", "instagram.com", "linkedin.com",
    "tripadvisor.com", "booking.com", "hotels.com", "expedia.com",
    "yahoo.com", "hotmail.com"
]

EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+\-]+@(?:gmail|yahoo|hotmail|outlook|icloud)\.com', re.IGNORECASE)

async def fetch_page_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
            if resp.status_code == 200:
                return resp.text
            return ""
    except Exception as e:
        # Subtle logging for network errors
        return ""

def extract_emails(text: str):
    if not text:
        return set()
    found = set(EMAIL_PATTERN.findall(text))
    filtered = set()
    for e in found:
        lower = e.lower()
        # Filter obvious junk
        if any(x in lower for x in ["noreply", "no-reply", "test@", "example", "user@", "email@", "name@"]):
            continue
        filtered.add(e)
    return filtered

async def ddgs_search(query: str, max_results: int = 15):
    """Run DuckDuckGo search synchronously in a thread."""
    def _search():
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results if results else []
        except Exception as e:
            logging.warning(f"DDGS search failed for '{query}': {e}")
            return []
    return await asyncio.to_thread(_search)

async def process_results(results, niche, location):
    inserted_count = 0
    if not results:
        return 0
        
    for r in results:
        url = r.get("href", "")
        snippet = (r.get("body", "") + " " + r.get("title", "")).lower()

        # Check snippet first
        emails = extract_emails(snippet)

        # If no email in snippet and not a skip domain, try fetching the page
        if not emails and url.startswith("http") and not any(skip in url for skip in SKIP_DOMAINS):
            logging.info(f"🌐 Visiting: {url[:60]}...")
            page_text = await fetch_page_text(url)
            emails = extract_emails(page_text)

        for email in emails:
            name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
            # Clean up numeric-only names
            if re.match(r'^\d+$', name):
                name = f"{niche} Business"
            
            inserted = await database.insert_lead(name=name, email=email, niche=niche, location=location)
            if inserted:
                logging.info(f"✅ NEW LEAD: {email} | {niche} | {location}")
                inserted_count += 1
            else:
                # Already exists
                pass

    return inserted_count

async def scrape_new_leads():
    total = 0
    # Randomize order to avoid patterns
    import random
    locs = list(LOCATIONS)
    random.shuffle(locs)
    
    for location in locs:
        for niche in NICHES:
            logging.info(f"🔍 Searching: {niche} in {location}...")

            queries = [
                f'"{niche}" {location} "@gmail.com" contact',
                f'site:facebook.com "{niche}" {location} gmail',
                f'"{niche}" {location} owner email gmail',
            ]

            for query in queries:
                results = await ddgs_search(query, max_results=15)
                if results:
                    count = await process_results(results, niche, location)
                    total += count
                    if total >= 10: # Stop early if we have enough for a few cycles
                        logging.info("Found enough leads for now. Wrapping up...")
                        return total
                await asyncio.sleep(2) # Polite delay between queries

    logging.info(f"Scraping cycle complete. Total new leads: {total}")
    return total

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    asyncio.run(scrape_new_leads())
