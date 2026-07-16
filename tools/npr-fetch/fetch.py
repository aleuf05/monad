#!/usr/bin/env python3
"""
Shared NPR fetch logic for Radio Console's two NPR content sources:
real-time headlines and podcast episodes. Both existed as separate scripts
(tools/npr-headlines/fetch.py, tools/npr-podcasts/fetch.py) solely to work
around the same problem -- NPR's feeds only grant CORS to apps.npr.org, so
fetching must happen server-side, not from the browser -- and were
duplicating the same urllib.request/User-Agent boilerplate. Consolidated
here; tools/npr-headlines/fetch.py and tools/npr-podcasts/fetch.py are now
thin wrappers that call into this module, kept at their exact original
paths because tools/npr-headlines/fetch.py has a live 15-minute crontab
entry pointing at it directly (`crontab -l`) -- changing that path would
require a crontab edit, which is the kind of infrastructure change this
project routes through the Lieutenant/cmd.sh, not an agent session.

Per NPR's RSS/podcast terms: feed content (titles, links, episode
metadata, and the enclosure URL a podcast feed itself publishes) may be
displayed/played on a personal/noncommercial site with attribution. The
podcast path streams the enclosure URL directly for client-side <audio>
playback -- it never downloads, stores, or re-hosts the audio file, so
nothing here redistributes NPR's audio.
"""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TIMEOUT_SECONDS = 10
ITUNES_NS = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

HEADLINES_FEED_URL = "https://feeds.npr.org/1001/rss.xml"
HEADLINES_OUTPUT_PATH = ROOT / "web/data/npr-headlines.json"
HEADLINES_MAX_ITEMS = 8

# Fixed and verified (each fetched live and its <title> checked) 2026-07-16
# -- not scraped from an unverified directory, so a bad/dead feed ID can't
# silently end up in the product.
PODCAST_SHOWS = [
    {"show_id": "npr-news-now", "feed_url": "https://feeds.npr.org/500005/podcast.xml"},
    {"show_id": "up-first", "feed_url": "https://feeds.npr.org/510318/podcast.xml"},
    {"show_id": "planet-money", "feed_url": "https://feeds.npr.org/510289/podcast.xml"},
    {"show_id": "the-indicator", "feed_url": "https://feeds.npr.org/510325/podcast.xml"},
    {"show_id": "fresh-air", "feed_url": "https://feeds.npr.org/381444908/podcast.xml"},
    {"show_id": "throughline", "feed_url": "https://feeds.npr.org/510333/podcast.xml"},
    {"show_id": "ted-radio-hour", "feed_url": "https://feeds.npr.org/510298/podcast.xml"},
    {"show_id": "short-wave", "feed_url": "https://feeds.npr.org/510351/podcast.xml"},
]
PODCASTS_OUTPUT_PATH = ROOT / "web/data/npr-podcasts.json"
PODCAST_MAX_EPISODES_PER_SHOW = 10


def fetch_feed(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Monad/1.0 (personal, noncommercial)"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


# --- Headlines ---

def parse_headline_items(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.findall("./channel/item")[:HEADLINES_MAX_ITEMS]:
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        pub_date = item.findtext("pubDate", default="").strip()
        if title and link:
            items.append({"title": title, "link": link, "pubDate": pub_date})
    return items


def fetch_headlines() -> int:
    try:
        xml_bytes = fetch_feed(HEADLINES_FEED_URL)
        items = parse_headline_items(xml_bytes)
    except Exception as error:
        # Report-only failure: leave any existing file in place rather than
        # overwrite good data with an empty result on a transient fetch error.
        print(f"npr-headlines fetch failed: {error}", file=sys.stderr)
        return 1

    # Do not rewrite the tracked live snapshot merely to advance fetched_at.
    # The 15-minute cron otherwise dirties Git even when NPR's actual items
    # are unchanged, which also invalidates commit-pinned commissioning work.
    if HEADLINES_OUTPUT_PATH.exists():
        try:
            existing = json.loads(HEADLINES_OUTPUT_PATH.read_text())
            if existing.get("items") == items:
                print(f"headlines unchanged; kept {HEADLINES_OUTPUT_PATH}")
                return 0
        except (OSError, json.JSONDecodeError):
            pass

    payload = {
        "source": "NPR News Headlines",
        "source_url": "https://www.npr.org/sections/news/",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    with open(HEADLINES_OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {len(items)} headlines to {HEADLINES_OUTPUT_PATH}")
    return 0


# --- Podcasts ---

def parse_podcast_show(xml_bytes: bytes, feed_url: str) -> dict:
    root = ET.fromstring(xml_bytes)
    channel = root.find("./channel")
    title = channel.findtext("title", default="").strip()
    link = channel.findtext("link", default="").strip()
    image_el = channel.find(f"{ITUNES_NS}image")
    image = image_el.get("href") if image_el is not None else None

    episodes = []
    for item in channel.findall("item")[:PODCAST_MAX_EPISODES_PER_SHOW]:
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


def fetch_podcasts() -> int:
    shows_out = []
    errors = []
    for show in PODCAST_SHOWS:
        try:
            xml_bytes = fetch_feed(show["feed_url"])
            parsed = parse_podcast_show(xml_bytes, show["feed_url"])
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
    with open(PODCASTS_OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    total_episodes = sum(len(s["episodes"]) for s in shows_out)
    print(f"wrote {len(shows_out)} shows ({total_episodes} episodes) to {PODCASTS_OUTPUT_PATH}")
    if errors:
        print("errors:", file=sys.stderr)
        for line in errors:
            print(f"  {line}", file=sys.stderr)
    return 0


def main() -> int:
    """No args: refresh both (for a single consolidated cron entry, should
    one ever replace the two current independent schedules). `headlines`
    or `podcasts`: refresh just that one, matching each thin wrapper's
    exact original single-purpose behavior.
    """
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "headlines":
        return fetch_headlines()
    if mode == "podcasts":
        return fetch_podcasts()
    if mode == "all":
        headlines_result = fetch_headlines()
        podcasts_result = fetch_podcasts()
        return headlines_result or podcasts_result
    print(f"unknown mode: {mode!r} (expected headlines, podcasts, or all)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
