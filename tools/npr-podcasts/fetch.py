#!/usr/bin/env python3
"""
Fetches a fixed, verified list of official NPR podcast RSS feeds and writes
the newest episodes (real audio enclosures, not headline text) to
web/data/npr-podcasts.json as a static file Radio Console can poll
same-origin (NPR's feeds only grant CORS to apps.npr.org, so a browser-side
fetch from cameronlampley.com is blocked -- this script is the server-side
hop that avoids that, same reason tools/npr-headlines/fetch.py exists).

Per NPR's RSS/podcast terms: feed content (titles, links, episode metadata,
and the enclosure URL the feed itself publishes) may be displayed and played
on a personal/noncommercial site with attribution. This writes the
enclosure URL through unmodified for direct client-side <audio> playback
streamed from NPR's own CDN -- it never downloads, stores, or re-hosts the
audio file itself, so nothing here redistributes NPR's audio; it only
references what the feed already ships for exactly this purpose.

Show list is fixed and verified (each fetched live and its <title> checked)
2026-07-16 -- not scraped from an unverified directory, so a bad/dead feed
ID can't silently end up in the product.
"""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

SHOWS = [
    {"show_id": "npr-news-now", "feed_url": "https://feeds.npr.org/500005/podcast.xml"},
    {"show_id": "up-first", "feed_url": "https://feeds.npr.org/510318/podcast.xml"},
    {"show_id": "planet-money", "feed_url": "https://feeds.npr.org/510289/podcast.xml"},
    {"show_id": "the-indicator", "feed_url": "https://feeds.npr.org/510325/podcast.xml"},
    {"show_id": "fresh-air", "feed_url": "https://feeds.npr.org/381444908/podcast.xml"},
    {"show_id": "throughline", "feed_url": "https://feeds.npr.org/510333/podcast.xml"},
    {"show_id": "ted-radio-hour", "feed_url": "https://feeds.npr.org/510298/podcast.xml"},
    {"show_id": "short-wave", "feed_url": "https://feeds.npr.org/510351/podcast.xml"},
]
OUTPUT_PATH = "/home/cgl/dev/monad/web/data/npr-podcasts.json"
MAX_EPISODES_PER_SHOW = 10
TIMEOUT_SECONDS = 10
ITUNES_NS = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Monad/1.0 (personal, noncommercial)"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def parse_show(xml_bytes: bytes, feed_url: str) -> dict:
    root = ET.fromstring(xml_bytes)
    channel = root.find("./channel")
    title = channel.findtext("title", default="").strip()
    link = channel.findtext("link", default="").strip()
    image_el = channel.find(f"{ITUNES_NS}image")
    image = image_el.get("href") if image_el is not None else None

    episodes = []
    for item in channel.findall("item")[:MAX_EPISODES_PER_SHOW]:
        ep_title = item.findtext("title", default="").strip()
        pub_date = item.findtext("pubDate", default="").strip()
        link_el = item.findtext("link", default="").strip()
        enclosure = item.find("enclosure")
        duration = item.findtext(f"{ITUNES_NS}duration", default="").strip()
        if not ep_title or enclosure is None or not enclosure.get("url"):
            continue
        episodes.append({
            "title": ep_title,
            "pubDate": pub_date,
            "link": link_el,
            "audio_url": enclosure.get("url"),
            "audio_type": enclosure.get("type", "audio/mpeg"),
            "duration_seconds": int(duration) if duration.isdigit() else None,
        })

    return {
        "title": title,
        "show_link": link,
        "feed_url": feed_url,
        "image": image,
        "episodes": episodes,
    }


def main() -> int:
    shows_out = []
    errors = []
    for show in SHOWS:
        try:
            xml_bytes = fetch_feed(show["feed_url"])
            parsed = parse_show(xml_bytes, show["feed_url"])
            parsed["show_id"] = show["show_id"]
            shows_out.append(parsed)
        except Exception as error:
            # Partial-failure tolerant: one dead/slow feed shouldn't drop
            # every other show's data -- report it and keep going.
            errors.append(f"{show['show_id']}: {error}")

    if not shows_out:
        print("npr-podcasts fetch failed: no shows fetched successfully", file=sys.stderr)
        for line in errors:
            print(f"  {line}", file=sys.stderr)
        return 1

    payload = {
        "source": "NPR Podcasts",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "shows": shows_out,
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    total_episodes = sum(len(s["episodes"]) for s in shows_out)
    print(f"wrote {len(shows_out)} shows ({total_episodes} episodes) to {OUTPUT_PATH}")
    if errors:
        print("errors:", file=sys.stderr)
        for line in errors:
            print(f"  {line}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
