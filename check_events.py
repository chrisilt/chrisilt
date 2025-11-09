#!/usr/bin/env python3
"""
EUGLOH Course Events Scraper
Periodically scrapes course registration pages, extracts new events,
and publishes them to an RSS feed and optional webhook.
"""

import os
import json
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlunparse
from xml.sax.saxutils import escape
import requests
from bs4 import BeautifulSoup


# Configuration from environment variables
TARGET_URL = os.environ.get(
    'TARGET_URL',
    'https://www.eugloh.eu/courses-trainings/?openRegistrations=%5Byes%5D'
)
# CSS selector for registration link buttons
# CUSTOMIZE THIS if the page structure changes or for different websites
REG_LINK_SELECTOR = os.environ.get(
    'REG_LINK_SELECTOR',
    'div.buttons-wrap:nth-child(3) > div:nth-child(1) > p:nth-child(1) > a:nth-child(1)'
)
# CSS selector for event title (searches in ancestors of registration link)
# CUSTOMIZE THIS to extract titles from different page structures
TITLE_SELECTOR = os.environ.get('TITLE_SELECTOR', 'h5.headline')
# CSS selector for event date (searches in ancestors of registration link)
# CUSTOMIZE THIS to extract dates from different page structures
DATE_SELECTOR = os.environ.get('DATE_SELECTOR', 'time, .date')

STATE_FILE = os.environ.get('STATE_FILE', 'seen.json')
FEED_FILE = os.environ.get('FEED_FILE', 'feed.xml')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
USER_AGENT = os.environ.get(
    'USER_AGENT',
    'Mozilla/5.0 (compatible; EUGLOH-Events-Bot/1.0)'
)
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '30'))


def normalize_url(url, base_url):
    """
    Convert relative URLs to absolute and strip query/fragment for stable IDs.
    """
    # Make absolute
    absolute_url = urljoin(base_url, url)
    # Parse and strip query and fragment for stable ID
    parsed = urlparse(absolute_url)
    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    return normalized, absolute_url


def extract_event_data(link_element, base_url):
    """
    Extract event data from a registration link element.
    Searches ancestor elements for title and date using configured selectors.
    
    Args:
        link_element: BeautifulSoup element containing the registration link
        base_url: Base URL for converting relative links to absolute
        
    Returns:
        dict with keys: id, link, title, date (or None if extraction fails)
    """
    try:
        # Get the registration link
        link_href = link_element.get('href', '')
        if not link_href:
            return None
            
        stable_id, full_link = normalize_url(link_href, base_url)
        
        # Search ancestors for title
        # IMPORTANT: If title extraction fails, adjust TITLE_SELECTOR environment variable
        title = None
        for ancestor in link_element.parents:
            title_elem = ancestor.select_one(TITLE_SELECTOR)
            if title_elem:
                title = title_elem.get_text(strip=True)
                break
        
        if not title:
            # Fallback: try to get link text or nearby text
            title = link_element.get_text(strip=True) or "Untitled Event"
        
        # Search ancestors for date
        # IMPORTANT: If date extraction fails, adjust DATE_SELECTOR environment variable
        date = None
        for ancestor in link_element.parents:
            date_elem = ancestor.select_one(DATE_SELECTOR)
            if date_elem:
                # Try datetime attribute first (for <time> elements)
                date = date_elem.get('datetime') or date_elem.get_text(strip=True)
                break
        
        if not date:
            date = "Date TBD"
        
        return {
            'id': stable_id,
            'link': full_link,
            'title': title,
            'date': date
        }
    except Exception as e:
        print(f"Error extracting event data: {e}", file=sys.stderr)
        return None


def load_seen_events():
    """Load previously seen event IDs from state file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Warning: Could not load state file: {e}", file=sys.stderr)
    return set()


def save_seen_events(seen_ids):
    """Save seen event IDs to state file."""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted(list(seen_ids)), f, indent=2)
    except Exception as e:
        print(f"Error saving state file: {e}", file=sys.stderr)
        sys.exit(1)


def post_to_webhook(event):
    """Post new event to webhook if configured."""
    if not WEBHOOK_URL:
        return
    
    try:
        payload = {
            'title': event['title'],
            'link': event['link'],
            'date': event['date'],
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        print(f"Posted to webhook: {event['title']}")
    except Exception as e:
        print(f"Warning: Failed to post to webhook: {e}", file=sys.stderr)


def generate_rss_item(event):
    """Generate RSS 2.0 item XML for an event."""
    # Escape XML special characters
    title = escape(event['title'])
    link = escape(event['link'])
    date_str = escape(event['date'])
    
    # Use current time as pubDate in RFC 822 format
    pub_date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    
    # Create description with date info
    description = escape(f"Registration Date: {date_str}")
    
    item = f"""  <item>
    <title>{title}</title>
    <link>{link}</link>
    <description>{description}</description>
    <pubDate>{pub_date}</pubDate>
    <guid isPermaLink="true">{link}</guid>
  </item>"""
    
    return item


def update_rss_feed(new_events):
    """Prepend new events to RSS feed file."""
    if not new_events:
        return
    
    # Read existing feed if it exists
    existing_items = []
    if os.path.exists(FEED_FILE):
        try:
            with open(FEED_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract existing items (simple approach: split on </item>)
                parts = content.split('</item>')
                for part in parts[:-1]:  # Last part is after final </item>
                    if '<item>' in part:
                        item_start = part.find('<item>')
                        existing_items.append(part[item_start:] + '</item>')
        except Exception as e:
            print(f"Warning: Could not read existing feed: {e}", file=sys.stderr)
    
    # Generate RSS 2.0 feed with new items prepended (newest first)
    new_items = [generate_rss_item(event) for event in reversed(new_events)]
    all_items = new_items + existing_items
    
    # Build complete feed
    feed_title = escape("EUGLOH Course Events")
    feed_link = escape(TARGET_URL)
    feed_description = escape("New course registration opportunities from EUGLOH")
    build_date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    
    feed_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{feed_title}</title>
    <link>{feed_link}</link>
    <description>{feed_description}</description>
    <lastBuildDate>{build_date}</lastBuildDate>
{''.join(all_items)}
  </channel>
</rss>
"""
    
    try:
        with open(FEED_FILE, 'w', encoding='utf-8') as f:
            f.write(feed_content)
        print(f"Updated RSS feed: {FEED_FILE}")
    except Exception as e:
        print(f"Error writing RSS feed: {e}", file=sys.stderr)
        sys.exit(1)


def scrape_events():
    """
    Main scraping function.
    Fetches the target URL, extracts registration links and event data,
    deduplicates against seen events, and returns new events.
    """
    print(f"Fetching: {TARGET_URL}")
    
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(TARGET_URL, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        sys.exit(1)
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all registration links using the configured selector
    link_elements = soup.select(REG_LINK_SELECTOR)
    print(f"Found {len(link_elements)} registration link(s)")
    
    # Extract event data from each link
    events = []
    for link_elem in link_elements:
        event = extract_event_data(link_elem, TARGET_URL)
        if event:
            events.append(event)
    
    print(f"Extracted {len(events)} event(s)")
    
    # Load seen events and filter for new ones
    seen_ids = load_seen_events()
    new_events = [e for e in events if e['id'] not in seen_ids]
    
    print(f"Found {len(new_events)} new event(s)")
    
    return new_events, seen_ids


def main():
    """Main entry point."""
    print("=" * 60)
    print("EUGLOH Course Events Scraper")
    print("=" * 60)
    print(f"Target URL: {TARGET_URL}")
    print(f"Registration Link Selector: {REG_LINK_SELECTOR}")
    print(f"Title Selector: {TITLE_SELECTOR}")
    print(f"Date Selector: {DATE_SELECTOR}")
    print(f"State File: {STATE_FILE}")
    print(f"Feed File: {FEED_FILE}")
    print(f"Webhook URL: {'(configured)' if WEBHOOK_URL else '(not set)'}")
    print("=" * 60)
    
    # Scrape and extract new events
    new_events, seen_ids = scrape_events()
    
    # Process new events
    if new_events:
        print("\nNew Events:")
        print("-" * 60)
        for event in new_events:
            print(f"Title: {event['title']}")
            print(f"Date: {event['date']}")
            print(f"Link: {event['link']}")
            print(f"ID: {event['id']}")
            print("-" * 60)
            
            # Post to webhook if configured
            post_to_webhook(event)
            
            # Add to seen set
            seen_ids.add(event['id'])
        
        # Update RSS feed
        update_rss_feed(new_events)
        
        # Save updated seen events
        save_seen_events(seen_ids)
        
        print(f"\n✓ Successfully processed {len(new_events)} new event(s)")
    else:
        print("\nNo new events found")
        # Ensure state file exists even if no new events
        save_seen_events(seen_ids)
    
    print("=" * 60)
    print("Done")


if __name__ == '__main__':
    main()
