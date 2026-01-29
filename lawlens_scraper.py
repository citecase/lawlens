import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime

# --- Configuration ---
TELEGRAM_URL = "https://t.me/s/Lawlens_IN_DHC"
APP_ID = "lawlens-dhc-sync"

def parse_legal_text(text):
    """
    Parses raw Telegram text into a structured dictionary without AI.
    Looks for common legal news patterns.
    """
    # Try to find a title (usually the first bolded line or the first line)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return None

    title = lines[0]
    # Clean up common prefixes from titles
    title = re.sub(r'^(JUST IN:|BREAKING:|UPDATE:)\s*', '', title, flags=re.I)
    
    # Try to extract a date (looks for DD.MM.YYYY or similar)
    date_match = re.search(r'(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})', text)
    date_str = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

    # Simple summary: use the first 2-3 lines after the title
    summary = " ".join(lines[1:3]) if len(lines) > 1 else "No summary available."
    
    # Extract Key Points (lines starting with - or •)
    key_points = [line.strip('- •') for line in lines if line.startswith(('-', '•'))]
    if not key_points and len(lines) > 3:
        key_points = lines[3:5] # Fallback to next lines

    # Basic Categorization based on keywords
    categories = []
    keywords = {
        "Criminal": ["bail", "ipc", "crpc", "arrest", "police", "fir"],
        "Civil": ["suit", "property", "contract", "recovery"],
        "Tech/IP": ["patent", "trademark", "copyright", "it act", "ai", "digital"],
        "Constitutional": ["article", "writ", "fundamental rights"],
        "Family": ["divorce", "maintenance", "custody"]
    }
    
    for cat, words in keywords.items():
        if any(word in text.lower() for word in words):
            categories.append(cat)
    
    if not categories:
        categories = ["General"]

    return {
        "title": title[:100], # Cap title length
        "date": date_str,
        "court": "Delhi High Court",
        "summary": summary,
        "key_points": key_points[:3],
        "categories": categories
    }

def scrape_telegram():
    """Scrapes the public web preview of the Telegram channel."""
    print(f"Fetching updates from {TELEGRAM_URL}...")
    try:
        response = requests.get(TELEGRAM_URL, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching Telegram: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    # Find message containers
    message_wrappers = soup.find_all("div", class_="tgme_widget_message_text")
    
    parsed_updates = []
    for wrapper in message_wrappers:
        raw_text = wrapper.get_text(separator="\n").strip()
        if len(raw_text) > 50: # Ignore very short messages (links only, etc.)
            data = parse_legal_text(raw_text)
            if data:
                parsed_updates.append(data)
                
    return parsed_updates

def update_files(new_data):
    """Merges new data with existing records and updates .json and .md files."""
    json_path = "lawlens.json"
    md_path = "lawlens.md"

    # Load existing data
    existing_data = []
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except:
            existing_data = []

    # De-duplication based on title
    existing_titles = {item['title'] for item in existing_data}
    added_count = 0
    for item in reversed(new_data): # Newest usually at bottom of page
        if item['title'] not in existing_titles:
            existing_data.insert(0, item)
            added_count += 1

    # Limit storage
    final_data = existing_data[:100]

    # Write JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)

    # Generate Markdown
    md_content = "# LawLens Delhi High Court Feed\n\n*Auto-updated via Regex Scraper (No AI).*\n\n"
    for item in final_data:
        md_content += f"## {item['title']}\n"
        md_content += f"- **Date:** {item['date']}\n"
        md_content += f"- **Category:** {', '.join(item['categories'])}\n\n"
        md_content += f"{item['summary']}\n\n"
        if item.get('key_points'):
            md_content += "### Key Points\n"
            for pt in item['key_points']:
                md_content += f"- {pt}\n"
        md_content += "\n---\n\n"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Sync complete. Added {added_count} new records.")

if __name__ == "__main__":
    updates = scrape_telegram()
    if updates:
        update_files(updates)
    else:
        print("No processable updates found.")
