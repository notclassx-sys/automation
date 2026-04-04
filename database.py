import json
import os
import asyncio
import logging

JSON_NAME = 'leads.json'

# Lock for concurrent access (mostly for local safety, GitHub Actions is single-threaded usually)
_lock = asyncio.Lock()

def _load_data():
    if not os.path.exists(JSON_NAME):
        return {"leads": [], "settings": {}}
    try:
        with open(JSON_NAME, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"leads": [], "settings": {}}

def _save_data(data):
    with open(JSON_NAME, 'w') as f:
        json.dump(data, f, indent=4)

async def init_db():
    async with _lock:
        if not os.path.exists(JSON_NAME):
            _save_data({"leads": [], "settings": {}})
        logging.info("JSON Database initialized.")

async def insert_lead(name, email, niche, location):
    async with _lock:
        data = _load_data()
        # Check if email already exists
        if any(lead['email'] == email for lead in data['leads']):
            return False

        new_lead = {
            "id": len(data['leads']) + 1,
            "name": name,
            "email": email,
            "niche": niche,
            "location": location,
            "status": "pending"
        }
        data['leads'].append(new_lead)
        _save_data(data)
        return True

async def clear_all_leads():
    async with _lock:
        data = _load_data()
        data['leads'] = []
        _save_data(data)
        logging.info("🧹 Database cleared: all leads removed.")

async def get_pending_leads(limit=5):
    async with _lock:
        data = _load_data()
        pending = [lead for lead in data['leads'] if lead.get('status') == 'pending']
        return pending[:limit]

async def mark_lead_sent(email):
    async with _lock:
        data = _load_data()
        for lead in data['leads']:
            if lead.get('email') == email:
                lead['status'] = 'sent'
                break
        _save_data(data)

async def save_setting(key, value):
    async with _lock:
        data = _load_data()
        data['settings'][key] = value
        _save_data(data)

async def get_setting(key):
    async with _lock:
        data = _load_data()
        return data['settings'].get(key)

async def update_last_run():
    """Update a timestamp in settings so there's always a change to commit."""
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with _lock:
        data = _load_data()
        data['settings']['last_run'] = now_str
        _save_data(data)
        logging.info(f"Database 'last_run' updated: {now_str}")

async def get_daily_sent_count():
    """Get the number of emails sent today."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    async with _lock:
        data = _load_data()
        if data['settings'].get('daily_sent_date') != today:
            data['settings']['daily_sent_date'] = today
            data['settings']['daily_sent_count'] = 0
            _save_data(data)
        return data['settings'].get('daily_sent_count', 0)

async def increment_daily_sent_count():
    """Increment the number of emails sent today."""
    async with _lock:
        data = _load_data()
        count = data['settings'].get('daily_sent_count', 0)
        data['settings']['daily_sent_count'] = count + 1
        _save_data(data)
