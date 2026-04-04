import os
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
import logging

def _send_email_sync(to_email, subject, body):
    sender_email = os.getenv("GMAIL_USER")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not sender_password:
        logging.error("Missing GMAIL_USER or GMAIL_APP_PASSWORD in .env")
        return False

    names = ["Monu Kumar", "Monu", "Monu K.", "Monu from Inityo"]
    from_name = random.choice(names)

    msg = MIMEMultipart()
    msg['From'] = f"{from_name} <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        logging.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")
        return False

async def send_email_async(to_email, subject, body):
    return await asyncio.to_thread(_send_email_sync, to_email, subject, body)
