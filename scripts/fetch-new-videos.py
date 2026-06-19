#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS feeds."""

import json
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
WATCH_BASE = "https://www.youtube.com/watch?v={}"
LOOKBACK_HOURS = 24


def load_json(path):
    if path.exists():
        return json.loads(path.read_text())
    return []


def fetch_rss(channel_id):
    url = RSS_BASE.format(channel_id)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read()
    except Exception as e:
        print(f"[warn] RSS fetch failed for {channel_id}: {e}", file=sys.stderr)
        return None


def parse_entries(xml_bytes, channel_name):
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(xml_bytes)
    entries = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        if video_id_el is None or title_el is None or published_el is None:
            continue

        published_str = published_el.text.strip()
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if published < cutoff:
            continue

        entries.append({
            "video_id": video_id_el.text.strip(),
            "title": title_el.text.strip(),
            "url": WATCH_BASE.format(video_id_el.text.strip()),
            "published": published_str,
            "channel": channel_name,
        })

    return entries


def main():
    channels = load_json(CHANNELS_FILE)
    processed_ids = set(load_json(PROCESSED_FILE))
    new_videos = []

    for ch in channels:
        xml_bytes = fetch_rss(ch["channel_id"])
        if not xml_bytes:
            continue
        entries = parse_entries(xml_bytes, ch["name"])
        for entry in entries:
            if entry["video_id"] not in processed_ids:
                new_videos.append(entry)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
