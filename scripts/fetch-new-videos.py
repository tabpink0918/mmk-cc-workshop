#!/usr/bin/env python3
"""
Fetch new videos from Korean stock market YouTube channels using RSS feeds.
Compares against data/processed.json to find unprocessed videos.
"""
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

CHANNELS = [
    {
        "name": "삼프로TV",
        "channel_id": "UChlv4GSd7OQl3js-jkLOnFA",
    },
    {
        "name": "한국경제TV",
        "channel_id": "UCF8AeLlUbEpKju6v1H6p8Eg",
    },
]

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            data = json.load(f)
        return set(data.get("processed_video_ids", []))
    return set()


def fetch_channel_videos(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
        root = ET.fromstring(content)
        videos = []
        for entry in root.findall("atom:entry", NS):
            vid_id_el = entry.find("yt:videoId", NS)
            title_el = entry.find("atom:title", NS)
            link_el = entry.find("atom:link", NS)
            published_el = entry.find("atom:published", NS)
            if vid_id_el is None:
                continue
            videos.append({
                "video_id": vid_id_el.text,
                "title": title_el.text if title_el is not None else "",
                "url": link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={vid_id_el.text}",
                "published": published_el.text if published_el is not None else "",
            })
        return videos
    except Exception as e:
        print(f"  [WARN] Failed to fetch channel {channel_id}: {e}", file=sys.stderr)
        return []


def main():
    processed = load_processed()
    new_videos = []

    for ch in CHANNELS:
        print(f"Checking channel: {ch['name']} ({ch['channel_id']})", file=sys.stderr)
        videos = fetch_channel_videos(ch["channel_id"])
        for v in videos[:5]:  # check most recent 5
            if v["video_id"] not in processed:
                v["channel_name"] = ch["name"]
                new_videos.append(v)

    # Output as JSON to stdout
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0 if new_videos else 0


if __name__ == "__main__":
    sys.exit(main())
