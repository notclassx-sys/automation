import os
import random
import logging

def load_keys():
    keys_str = os.getenv("GROQ_KEYS", "")
    return [k.strip() for k in keys_str.split(',') if k.strip()]

GROQ_KEYS = load_keys()
_key_index = 0

def get_next_key():
    """Round-robin key rotation."""
    global _key_index
    if not GROQ_KEYS:
        return None
    key = GROQ_KEYS[_key_index % len(GROQ_KEYS)]
    _key_index += 1
    return key

async def generate_email_content(lead_name: str, lead_niche: str, lead_location: str) -> str:
    script_body = (
        f"Noticed your business has strong potential, but most companies lose leads due to low-converting websites and lack of automation.\n\n"
        f"At https://inityo.in, we build scalable websites, apps, and AI automation systems designed to convert visitors into paying customers — especially for markets like the US, London, and Dubai.\n\n"
        f"✔ 20+ scalable websites & applications delivered\n"
        f"✔ AI-powered lead capture + follow-up automation\n"
        f"✔ 180+ real-world implementations (web, app, AI systems)\n\n"
        f"Recent insight: even a 10–20% conversion improvement can significantly increase revenue without increasing ad spend.\n\n"
        f"If you’re open, I can share 2–3 quick ideas tailored to your business or a short audit.\n\n"
        f"Reply “YES” and I’ll send it.\n\n"
        f"– Monu Kumar\n"
        f"https://inityo.in\n"
        f"https://www.instagram.com/hack_yhacker/"
    )
    
    greeting = f"Hi {lead_name} from {lead_location},\n\n"
    fallback = greeting + script_body

    key = get_next_key()
    if not key:
        return fallback

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=key)

        system_prompt = (
            "You are Monu Kumar, owner of https://inityo.in. Your mission is to send professional cold emails. "
            "Use the following structure specifically:\n"
            f"1. Greeting: {greeting}\n"
            "2. Body: Use the provided script but slightly personalize the first sentence to better fit the business type (niche) if possible. "
            "Keep the core facts and links exactly as they are.\n\n"
            "Script to follow:\n" + script_body
        )

        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Business: {lead_name}\nType: {lead_niche}\nLocation: {lead_location}"}
            ],
            temperature=0.7,
            max_tokens=400,
        )
        return completion.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"Groq API Error (key rotation in effect): {e}")
        return fallback
