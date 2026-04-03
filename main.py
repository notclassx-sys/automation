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
    logging.info("Starting execution cycle.")
    
    try:
        # 1. Fresh Scraping: Find new leads (scraper automatically skips existing emails)
        logging.info("🔍 Scraping fresh leads...")
        await scraper.scrape_new_leads(limit=5)
        
        # 2. Get the new pending leads
        pending_leads = await database.get_pending_leads(limit=5)
        
        if not pending_leads:
            logging.warning("No new pending leads found. Exiting cycle.")
            return

        logging.info(f"Processing {len(pending_leads)} pending leads.")
        
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
                # Mark as sent so we don't contact them again in future runs
                await database.mark_lead_sent(lead['email'])
                await asyncio.sleep(5) # Small delay to respect Gmail limits
            else:
                logging.warning(f"Failed to send email to: {lead['email']}")
                
        logging.info("Execution cycle complete. All contacted leads are now marked as 'sent'.")
            
    except Exception as e:
        logging.error(f"Error during execution: {e}")
    finally:
        # Always update last_run to ensure a commit happens on GitHub
        await database.update_last_run()

if __name__ == "__main__":
    try:
        asyncio.run(execute_one_cycle())
    except Exception as e:
        logging.error(f"Critical System Error: {e}")
