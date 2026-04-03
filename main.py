import asyncio
import logging
from dotenv import load_dotenv

# Load env before importing other modules that rely on it
load_dotenv()

import database
import scraper
import groq_engine
import mailer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def execute_one_cycle():
    await database.init_db()
    logging.info("Starting one-shot execution cycle for GitHub Actions.")
    
    try:
        # 1. Check pending leads
        pending_leads = await database.get_pending_leads(limit=5)
        
        # 2. If not enough leads, run scraper
        if len(pending_leads) < 5:
            logging.info(f"Only {len(pending_leads)} leads pending. Running scraper to find more...")
            await scraper.scrape_new_leads()
            pending_leads = await database.get_pending_leads(limit=5)
        
        if not pending_leads:
            logging.warning("No leads found after scraping. Exiting cycle.")
            return

        logging.info(f"Processing {len(pending_leads)} leads for this execution.")
        
        # 3. Process and send emails
        for lead in pending_leads:
            # Generate Email
            email_body = await groq_engine.generate_email_content(
                lead_name=lead['name'],
                lead_niche=lead['niche'],
                lead_location=lead['location']
            )
            
            # Send Email
            subject = f"Monu Kumar - Helping your {lead['niche']} business grow"
            success = await mailer.send_email_async(
                to_email=lead['email'],
                subject=subject,
                body=email_body
            )
            
            if success:
                await database.mark_lead_sent(lead['id'])
                logging.info(f"Successfully processed lead: {lead['email']}")
                await asyncio.sleep(5) # Small delay to not anger Gmail's smtp limit
                
        logging.info("Execution cycle complete. All scheduled emails sent.")
            
    except Exception as e:
        logging.error(f"Error during execution: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(execute_one_cycle())
    except Exception as e:
        logging.error(f"Critical System Error: {e}")
