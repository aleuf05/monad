#!/usr/bin/env python3
"""
Fetches NPR's public "NPR Topics: News" RSS feed and writes the latest
headlines to web/data/npr-headlines.json as a static file the Radio
Console can poll same-origin (NPR's feed only grants CORS to
apps.npr.org, so a browser-side fetch from cameronlampley.com is
blocked -- this script is the server-side hop that avoids that).

Per NPR's RSS terms of use: headlines, links, and other feed content may
be displayed on a personal/noncommercial site with attribution and
without modification; NPR audio files may not be redistributed beyond
what ships in the feed itself. This script writes title/link/pubDate
only -- no audio, no full article text.
"""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEED_URL = "https://feeds.npr.org/1001/rss.xml"
OUTPUT_PATH = "/home/cgl/dev/monad/web/data/npr-headlines.json"
MAX_ITEMS = 8
TIMEOUT_SECONDS = 10


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Monad/1.0 (personal, noncommercial)"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def parse_items(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.findall("./channel/item")[:MAX_ITEMS]:
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        pub_date = item.findtext("pubDate", default="").strip()
        if title and link:
            items.append({"title": title, "link": link, "pubDate": pub_date})
    return items


def main() -> int:
    try:
        xml_bytes = fetch_feed(FEED_URL)
        items = parse_items(xml_bytes)
    except Exception as error:
        # Report-only failure: leave any existing file in place rather than
        # overwrite good data with an empty result on a transient fetch error.
        print(f"npr-headlines fetch failed: {error}", file=sys.stderr)
        return 1

    payload = {
        "source": "NPR News Headlines",
        "source_url": "https://www.npr.org/sections/news/",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {len(items)} headlines to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
