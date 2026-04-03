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
    logging.info("Starting fresh execution cycle for GitHub Actions.")
    
    try:
        # 0. Clear old state to ensure full freshness
        await database.clear_all_leads()

        # 1. Fresh Scraping: Always find 5 new leads
        logging.info("🔍 Scraping 5 fresh leads for this session...")
        await scraper.scrape_new_leads(limit=5)
        
        # 2. Get the new leads
        pending_leads = await database.get_pending_leads(limit=5)
        
        if not pending_leads:
            logging.warning("No leads found during scraping. Exiting cycle.")
            return

        logging.info(f"Processing {len(pending_leads)} fresh leads.")
        
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
                logging.info(f"Successfully sent email to: {lead['email']}")
                # We don't mark as sent here because we'll clear everything at the end
                await asyncio.sleep(5) # Small delay to not anger Gmail's smtp limit
            else:
                logging.warning(f"Failed to send email to: {lead['email']}")
                
        # 4. Final Cleanup: Clear leads.json so storage stays empty between runs
        await database.clear_all_leads()
        logging.info("Execution cycle complete. Storage cleared.")
            
    except Exception as e:
        logging.error(f"Error during execution: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(execute_one_cycle())
    except Exception as e:
        logging.error(f"Critical System Error: {e}")
