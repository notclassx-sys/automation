import asyncio
import re
import logging
import httpx
import database

# Expanded list of international cities
LOCATIONS = [
    # USA
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "Austin",
    # UK
    "London", "Birmingham", "Manchester", "Glasgow", "Liverpool", "Leeds", "Sheffield", "Bristol", "Leicester", "Edinburgh",
    # Australia
    "Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast", "Canberra", "Newcastle", "Hobart", "Darwin",
    # Canada
    "Toronto", "Montreal", "Vancouver", "Ottawa", "Calgary", "Edmonton", "Winnipeg", "Quebec City", "Hamilton", "Kitchener",
    # Mexico
    "Mexico City", "Guadalajara", "Monterrey", "Puebla", "Tijuana", "Leon", "Juarez", "Zapopan", "Merida", "Cancun",
    # Others
    "Dubai", "Abu Dhabi", "Singapore", "Tokyo", "Berlin", "Paris", "Rome", "Madrid", "Barcelona", "Amsterdam"
]

NICHES = [
    "Real Estate", "Hospital", "Hotel", "Restaurant", "Cleaning Service", "Plumber", "Auto Repair",
    "Dentist", "Accountant", "Lawyer", "HVAC Service", "Gym & Fitness", "Spa & Wellness", "Photographer",
    "Electrician", "Roofer", "Landscaping", "Interior Designer", "Veterinarian", "Locksmith", "Architecture",
    "Flooring Contractor", "Pest Control", "Moving Company", "Bakery", "Coffee Shop", "Consulting", "Software Agency"
]

# Stricter domain skip list
SKIP_DOMAINS = [
    "duckduckgo.com", "google.com", "yelp.com", "wikipedia.org",
    "yellowpages.com", "facebook.com", "instagram.com", "linkedin.com",
    "tripadvisor.com", "booking.com", "hotels.com", "expedia.com",
    "yahoo.com", "hotmail.com", "pinterest.com", "twitter.com"
]

# Stricter pattern: local part must be at least 3 characters.
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+\-]{3,}@(?:gmail|yahoo|hotmail|outlook|icloud)\.com', re.IGNORECASE)

async def fetch_page_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
            if resp.status_code == 200:
                return resp.text
            return ""
    except Exception:
        return ""

def extract_emails(text: str):
    if not text:
        return set()
    found = set(EMAIL_PATTERN.findall(text))
    filtered = set()
    for e in found:
        lower = e.lower()
        # Filter obvious junk
        if any(x in lower for x in ["noreply", "no-reply", "test@", "example", "user@", "email@", "name@", "info@", "admin@", "sales@", "support@", "hr@"]):
            continue
        
        # Ensure it doesn't look like code or a fragment (e.g. starting with a dot or underscore)
        local_part = e.split('@')[0]
        if local_part.startswith(('.', '_', '+')) or local_part.endswith(('.', '_', '+')):
            continue
            
        filtered.add(e)
    return filtered

async def ddgs_search(query: str, max_results: int = 15):
    """Run DuckDuckGo search synchronously in a thread with 3 retries."""
    def _search():
        from duckduckgo_search import DDGS
        for attempt in range(1, 4):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
                    if results:
                        return results
                    # If empty
                    logging.warning(f"Attempt {attempt}: No results for '{query}'")
                    import time
                    time.sleep(2)
            except Exception as e:
                logging.warning(f"Attempt {attempt} search failed: {e}")
                import time
                time.sleep(2)
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

async def scrape_new_leads(limit: int = 10):
    total = 0
    
    # Load current indices for rotation
    loc_idx = await database.get_setting("location_index") or 0
    niche_idx = await database.get_setting("niche_index") or 0
    
    # Ensure they are within range
    loc_idx = loc_idx % len(LOCATIONS)
    niche_idx = niche_idx % len(NICHES)
    
    logging.info(f"🔄 Starting rotation cycle at: Location Index {loc_idx}, Niche Index {niche_idx}")
    
    # We will try up to 3 location-niche pairs in one run or until limit is reached
    pairs_searched = 0
    
    while total < limit and pairs_searched < 3:
        location = LOCATIONS[loc_idx]
        niche = NICHES[niche_idx]
        
        logging.info(f"🔍 SEARCHING: '{niche}' in '{location}'...")
        
        queries = [
            f'{niche} {location} gmail.com contact',
            f'site:facebook.com {niche} {location} "gmail.com"',
            f'{niche} in {location} email gmail contact',
        ]
        
        for query in queries:
            results = await ddgs_search(query, max_results=15)
            if results:
                count = await process_results(results, niche, location)
                total += count
                if total >= limit:
                    break
            await asyncio.sleep(2)
            
        # Increment indices for rotation
        # We rotate niche every time, but location only after all niches are exhausted for that location
        niche_idx += 1
        if niche_idx >= len(NICHES):
            niche_idx = 0
            loc_idx = (loc_idx + 1) % len(LOCATIONS)
        
        pairs_searched += 1
        
    # Save indices for next 30-minute run
    await database.save_setting("location_index", loc_idx)
    await database.save_setting("niche_index", niche_idx)
    
    logging.info(f"Scraping cycle complete. Total new leads: {total}. Updated Indices: {loc_idx}, {niche_idx}")
    return total

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    asyncio.run(scrape_new_leads())
