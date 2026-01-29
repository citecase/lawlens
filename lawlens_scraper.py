import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime

# --- Configuration ---
COURTS = {
    "Delhi High Court": "https://t.me/s/Lawlens_IN_DHC",
    "Bombay High Court": "https://t.me/s/Lawlens_IN_BHC",
    "Allahabad High Court": "https://t.me/s/Lawlens_IN_AHC",
    "Madras High Court": "https://t.me/s/Lawlens_IN_MHC",
    "Karnataka High Court": "https://t.me/s/Lawlens_IN_KAHC",
    "Patna High Court": "https://t.me/s/Lawlens_IN_PHC",
    "Gujarat High Court": "https://t.me/s/Lawlens_IN_GHC"
}

def parse_legal_text(text, court_name, msg_element):
    """
    Parses raw Telegram text and extracts links.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return None

    # Extract the source link from the message context if possible
    source_link = None
    # Look for the 'tgme_widget_message_date' link which is the permanent link to the post
    parent = msg_element.find_parent("div", class_="tgme_widget_message")
    if parent:
        link_tag = parent.find("a", class_="tgme_widget_message_date")
        if link_tag and link_tag.has_attr('href'):
            source_link = link_tag['href']

    title = lines[0]
    title = re.sub(r'^(JUST IN:|BREAKING:|UPDATE:)\s*', '', title, flags=re.I)
    
    date_match = re.search(r'(\d{1,2}[\.\/]\d{1,2}[\.\/]\d{2,4})', text)
    date_str = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

    summary = " ".join(lines[1:3]) if len(lines) > 1 else "No summary available."
    
    key_points = [line.strip('- •') for line in lines if line.startswith(('-', '•'))]
    if not key_points and len(lines) > 3:
        key_points = lines[3:5]

    categories = []
    keywords = {
        "Criminal": ["bail", "ipc", "crpc", "arrest", "police", "fir", "quashing"],
        "Civil": ["suit", "property", "contract", "recovery", "injunction"],
        "Tech/IP": ["patent", "trademark", "copyright", "it act", "ai", "digital", "privacy"],
        "Constitutional": ["article", "writ", "fundamental rights", "petition"],
        "Family": ["divorce", "maintenance", "custody", "matrimonial"]
    }
    
    for cat, words in keywords.items():
        if any(word in text.lower() for word in words):
            categories.append(cat)
    
    if not categories:
        categories = ["General"]

    return {
        "title": title[:120],
        "date": date_str,
        "court": court_name,
        "summary": summary,
        "key_points": key_points[:3],
        "categories": categories,
        "link": source_link
    }

def scrape_court(court_name, url):
    """Scrapes a specific court's telegram feed."""
    print(f"Fetching {court_name} updates...")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching {court_name}: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    message_wrappers = soup.find_all("div", class_="tgme_widget_message_text")
    
    parsed_updates = []
    for wrapper in message_wrappers:
        raw_text = wrapper.get_text(separator="\n").strip()
        if len(raw_text) > 60:
            data = parse_legal_text(raw_text, court_name, wrapper)
            if data:
                parsed_updates.append(data)
                
    return parsed_updates

def update_files(all_new_data):
    """Merges new data from all courts and updates files."""
    json_path = "lawlens.json"
    md_path = "lawlens.md"

    existing_data = []
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except:
            existing_data = []

    # De-duplication using title + court
    existing_keys = {f"{item['title']}-{item['court']}" for item in existing_data}
    added_count = 0
    
    for item in all_new_data:
        key = f"{item['title']}-{item['court']}"
        if key not in existing_keys:
            existing_data.insert(0, item)
            added_count += 1

    # Keep a manageable history
    final_data = existing_data[:200]

    # Write JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)

    # Generate Markdown grouped by court
    md_content = "# LawLens High Court Intelligence Feed\n\n*Aggregated legal updates from 7 High Courts (No AI).*\n\n"
    
    for court in COURTS.keys():
        court_items = [i for i in final_data if i['court'] == court]
        if court_items:
            md_content += f"## {court}\n"
            for item in court_items[:10]:
                md_content += f"### [{item['title']}]({item.get('link', '#')})\n"
                md_content += f"- **Date:** {item['date']}\n"
                md_content += f"- **Category:** {', '.join(item['categories'])}\n"
                if item.get('link'):
                    md_content += f"- **Source:** [View on Telegram]({item['link']})\n\n"
                else:
                    md_content += "\n"
                md_content += f"{item['summary']}\n\n"
                if item.get('key_points'):
                    for pt in item['key_points']:
                        md_content += f"- {pt}\n"
                md_content += "\n"
            md_content += "---\n\n"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Sync complete. Added {added_count} new records across all courts.")

if __name__ == "__main__":
    combined_data = []
    for name, url in COURTS.items():
        combined_data.extend(scrape_court(name, url))
    
    if combined_data:
        update_files(combined_data)
    else:
        print("No new updates found from any source.")
