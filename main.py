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
        # Check Daily Limit
        max_daily = int(os.getenv("MAX_DAILY_EMAILS", "15"))
        current_daily = await database.get_daily_sent_count()
        
        if current_daily >= max_daily:
            logging.warning(f"🛑 Daily limit reached ({current_daily}/{max_daily}). Stopping cycle for safety.")
            return

        # 1. Fresh Scraping: Find new leads
        logging.info("🔍 Scraping fresh leads...")
        await scraper.scrape_new_leads(limit=2) # Only scrape a few at a time
        
        # 2. Get the new pending leads
        # We only send 1 or 2 per cycle to stay 100% safe
        remaining_today = max_daily - current_daily
        batch_limit = min(2, remaining_today)
        
        pending_leads = await database.get_pending_leads(limit=batch_limit)
        
        if not pending_leads:
            logging.warning("No new pending leads found. Exiting cycle.")
            return

        logging.info(f"Processing {len(pending_leads)} pending leads. (Daily Progress: {current_daily}/{max_daily})")
        
        import random
        # 3. Process and send emails
        for i, lead in enumerate(pending_leads):
            # Generate Email (Subject + Body)
            subject, email_body = await groq_engine.generate_email_content(
                lead_name=lead['name'],
                lead_niche=lead['niche'],
                lead_location=lead['location']
            )
            
            # Send Email
            success = await mailer.send_email_async(
                to_email=lead['email'],
                subject=subject,
                body=email_body
            )
            
            if success:
                logging.info(f"✅ Successfully sent email to: {lead['email']}")
                await database.mark_lead_sent(lead['email'])
                await database.increment_daily_sent_count()
                
                # If there's another email in the batch, wait 10-30 minutes
                if i < len(pending_leads) - 1:
                    delay_mins = random.randint(10, 30)
                    logging.info(f"⏳ Waiting {delay_mins} minutes before next email for 100% safety...")
                    await asyncio.sleep(delay_mins * 60)
            else:
                logging.warning(f"❌ Failed to send email to: {lead['email']}")
                
        logging.info("Execution cycle complete.")
            
    except Exception as e:
        logging.error(f"Error during execution: {e}")
    finally:
        await database.update_last_run()

if __name__ == "__main__":
    try:
        asyncio.run(execute_one_cycle())
    except Exception as e:
        logging.error(f"Critical System Error: {e}")
