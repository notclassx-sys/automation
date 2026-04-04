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

async def generate_email_content(lead_name: str, lead_niche: str, lead_location: str):
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

        # 100% Safety: Randomly decide whether to include links in this variation
        include_links = random.random() > 0.3 # 70% chance to include links
        
        system_prompt = (
            "You are Monu Kumar, owner of Inityo (https://inityo.in). Your mission is to send professional cold emails. "
            "Use the following structure specifically:\n"
            "1. Subject: Create a unique, catchy subject line related to the niche.\n"
            f"2. Greeting: {greeting}\n"
            "3. Body: Personalize the body to fit the business type (niche). "
            "Keep the tone professional but helpful. "
            + ("Include the links: https://inityo.in and https://www.instagram.com/hack_yhacker/" if include_links else "Do NOT include any clickable links (http/https). Just mention 'Inityo'.") +
            "\n\nReturn the response in this format:\nSubject: [Subject Here]\n\n[Body Here]"
        )

        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Business: {lead_name}\nType: {lead_niche}\nLocation: {lead_location}"}
            ],
            temperature=0.8, # Higher temperature for more variance
            max_tokens=500,
        )
        content = completion.choices[0].message.content.strip()
        
        # Parse subject and body
        if "Subject:" in content:
            parts = content.split("\n\n", 1)
            subject = parts[0].replace("Subject:", "").strip()
            body = parts[1] if len(parts) > 1 else content
            return subject, body
        
        return f"Helping your {lead_niche} business grow", content

    except Exception as e:
        logging.error(f"Groq API Error (key rotation in effect): {e}")
        return f"Helping your {lead_niche} business grow", fallback
