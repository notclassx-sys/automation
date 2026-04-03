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
    fallback = (
        f"Hi {lead_name},\n\n"
        f"I'm Monu Kumar, a Web & App Developer. I noticed your {lead_niche} business in {lead_location} "
        f"doesn't have a website yet. I can help you build a professional website, mobile app, or AI chatbot "
        f"to grow your business online.\n\n"
        f"Would you be open to a quick 5-minute chat?\n\n"
        f"Best,\nMonu Kumar\nWeb Dev | App Dev | AI Agents & Chatbots"
    )

    key = get_next_key()
    if not key:
        return fallback

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=key)

        system_prompt = (
            "You are Monu Kumar, a professional developer offering: Web Development, App Development, "
            "Business Management Systems, Chatbots, and AI Agents. "
            "Write a short cold email (max 80 words) to a business owner who has NO website. "
            "Offer to help them get online. Be friendly, concise, and end with a soft call to action. "
            "Do NOT write a subject line. Sign off as 'Monu Kumar'."
        )

        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Business: {lead_name}\nType: {lead_niche}\nLocation: {lead_location}"}
            ],
            temperature=0.75,
            max_tokens=200,
        )
        return completion.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"Groq API Error (key rotation in effect): {e}")
        return fallback
