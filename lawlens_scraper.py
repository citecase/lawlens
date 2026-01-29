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
    Parses raw Telegram text and extracts Judgment URLs from the body.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return None

    # Priority 1: Extract actual URLs from the message body (Judgment links)
    # Most legal news channels include a link like bit.ly or a direct portal link
    body_links = re.findall(r'(https?://\S+)', text)
    judgment_link = None
    
    if body_links:
        # Filter out common Telegram/sharing links to find the actual source
        for link in body_links:
            if "t.me" not in link:
                judgment_link = link
                break
        if not judgment_link:
            judgment_link = body_links[0]

    # Priority 2: Fallback to the Telegram post link if no URL found in text
    if not judgment_link:
        parent = msg_element.find_parent("div", class_="tgme_widget_message")
        if parent:
            link_tag = parent.find("a", class_="tgme_widget_message_date")
            if link_tag and link_tag.has_attr('href'):
                judgment_link = link_tag['href']

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
        "link": judgment_link
    }

# ... (Rest of the scrape_court and update_files functions remain the same)
