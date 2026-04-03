import asyncio
import os
from dotenv import load_dotenv
import groq_engine

load_dotenv()

async def test_generation():
    name = "Davegmills70"
    niche = "Hospital"
    location = "USA"
    
    print(f"--- Generating for {name} ({niche}) in {location} ---")
    content = await groq_engine.generate_email_content(name, niche, location)
    
    with open("test_output.txt", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("Content saved to test_output.txt")
    print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_generation())
