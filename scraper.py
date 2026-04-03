import asyncio
import re
from playwright.async_api import async_playwright
import database
import logging

# Target locations and niches
LOCATIONS = ["USA", "Mexico", "UK"]
NICHES = ["Real Estates", "Hospitals", "Hotels", "Restaurants"]

async def find_emails(page, query):
    await page.goto(f"https://duckduckgo.com/html/?q={query}", wait_until="networkidle")
    content = await page.content()
    
    # Simple regex to find emails
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = set(re.findall(email_pattern, content))
    
    # Try to extract snippet texts to guess the business name
    leads = []
    for email in emails:
        # Ignore common dummy emails
        if "example.com" in email or "duckduckgo" in email:
            continue
        # For a headless simple approach, we'll use the email prefix as a placeholder business name
        # if we can't perfectly parse the HTML snippet.
        name = email.split('@')[0].replace('.', ' ').capitalize()
        leads.append({"name": name, "email": email})
        
    return leads

async def scrape_new_leads():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for location in LOCATIONS:
            for niche in NICHES:
                logging.info(f"Scraping for {niche} in {location}...")
                # Search footprint focusing on free email providers to guarantee email presence, 
                # and excluding common website signatures to target those without websites.
                query = f'"{niche}" "{location}" "@gmail.com" OR "@yahoo.com" -http -www'
                
                try:
                    leads = await find_emails(page, query)
                    for lead in leads:
                        # Insert into database
                        inserted = await database.insert_lead(
                            name=lead['name'],
                            email=lead['email'],
                            niche=niche,
                            location=location
                        )
                        if inserted:
                            logging.info(f"Found new lead: {lead['email']}")
                except Exception as e:
                    logging.error(f"Scraping Error: {e}")
                    
                await asyncio.sleep(5)  # anti-bot delay
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_new_leads())
