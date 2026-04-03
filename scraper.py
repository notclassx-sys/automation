import asyncio
import re
from duckduckgo_search import DDGS
import database
import logging

LOCATIONS = ["USA", "Mexico", "UK"]
NICHES = ["Real Estates", "Hospitals", "Hotels", "Restaurants"]

async def scrape_new_leads():
    # duckduckgo_search is synchronous block, use in asyncio to_thread if necessary
    # Since we are one-shot execution, we can just run it synchronously
    for location in LOCATIONS:
        for niche in NICHES:
            logging.info(f"Scraping for {niche} in {location} using API...")
            query = f'"{niche}" "{location}" "@gmail.com" OR "@yahoo.com" -http -www'
            
            try:
                # DDGS limits requests nicely
                results = DDGS().text(query, max_results=30)
                if not results:
                    continue
                
                for r in results:
                    content = r.get('body', '') + ' ' + r.get('title', '')
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    emails = set(re.findall(email_pattern, content))
                    
                    for email in emails:
                        if "example.com" in email or "duckduckgo" in email:
                            continue
                            
                        # Use email prefix as a placeholder business name
                        name = email.split('@')[0].replace('.', ' ').capitalize()
                        
                        inserted = await database.insert_lead(
                            name=name,
                            email=email,
                            niche=niche,
                            location=location
                        )
                        if inserted:
                            logging.info(f"Found new lead: {email}")
                            
            except Exception as e:
                logging.error(f"Scraping API Error: {e}")
                
            await asyncio.sleep(3)  # Respect rate limits

if __name__ == "__main__":
    asyncio.run(scrape_new_leads())
