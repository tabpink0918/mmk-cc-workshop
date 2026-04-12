#!/usr/bin/env python3
"""
Fetch new videos from Korean stock market YouTube channels.
Compares against data/processed.json and prints new video info as JSON.
"""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.error

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
# Only consider videos published within the last N days
LOOKBACK_DAYS = 3


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        print(f"  [WARN] Failed to fetch RSS for {channel_id}: {e}", file=sys.stderr)
        return None


def parse_rss(data):
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(data)
    entries = []
    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if video_id_el is None or title_el is None or published_el is None:
            continue

        published_str = published_el.text.strip()
        # Parse ISO 8601: 2024-04-10T12:00:00+00:00
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        entries.append(
            {
                "video_id": video_id_el.text.strip(),
                "title": title_el.text.strip(),
                "published": published_str,
                "url": f"https://www.youtube.com/watch?v={video_id_el.text.strip()}",
                "published_dt": published,
            }
        )
    return entries


def main():
    channels = load_json(CHANNELS_FILE)
    processed = set(load_json(PROCESSED_FILE))

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    new_videos = []

    for ch in channels:
        channel_id = ch["channel_id"]
        channel_name = ch["name"]
        print(f"Checking {channel_name} ({channel_id})...", file=sys.stderr)

        rss_data = fetch_rss(channel_id)
        if rss_data is None:
            continue

        entries = parse_rss(rss_data)
        for entry in entries:
            if entry["video_id"] in processed:
                continue
            if entry["published_dt"] < cutoff:
                continue
            video = {
                "video_id": entry["video_id"],
                "title": entry["title"],
                "published": entry["published"],
                "url": entry["url"],
                "channel": channel_name,
            }
            new_videos.append(video)
            print(
                f"  [NEW] {entry['title']} ({entry['video_id']})", file=sys.stderr
            )

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
