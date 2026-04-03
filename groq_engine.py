import os
import random
from groq import AsyncGroq

def load_keys():
    keys_str = os.getenv("GROQ_KEYS")
    if not keys_str:
        return []
    return [k.strip() for k in keys_str.split(',') if k.strip()]

GROQ_KEYS = load_keys()

async def generate_email_content(lead_name, lead_niche, lead_location):
    if not GROQ_KEYS:
        return f"Hi {lead_name},\n\nI'm Monu Kumar. I noticed your {lead_niche} business doesn't have a website. I provide Web Dev, App Dev, and AI Business Chatbots. Let's chat!\n\nBest,\nMonu Kumar"
    
    selected_key = random.choice(GROQ_KEYS)
    client = AsyncGroq(api_key=selected_key)
    
    system_prompt = (
        "You are Monu Kumar, an expert developer who provides Web Development, App Development, Business Management, Chatbots, and AI Agents. "
        "Your goal is to write a short, highly-converting personalized cold email (under 100 words) to a business owner. "
        "You noticed they do NOT have a website and you want to offer them your services to digitize their business. "
        "Keep it friendly and professional. Do NOT write a subject line. Do NOT use placeholders. Sign off as 'Monu Kumar'."
    )
    
    user_prompt = f"Business Name: {lead_name}\nNiche: {lead_niche}\nLocation: {lead_location}"
    
    try:
        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=300,
            top_p=1,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq API Error: {e}")
        return f"Hi {lead_name},\n\nI'm Monu Kumar. I noticed your {lead_niche} in {lead_location} doesn't have a website yet. I specialize in Web Dev, App Dev, Business Management Chatbots, and AI Agents to help businesses grow. Would you be open to a quick chat?\n\nBest,\nMonu Kumar"
