#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS."""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"
PROCESSED_FILE = DATA_DIR / "processed.json"

DAYS_BACK = 3


def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return set(json.load(f).get("processed_ids", []))
    return set()


def load_channels():
    with open(CHANNELS_FILE) as f:
        return json.load(f)


def fetch_channel_videos(channel_id, days_back=DAYS_BACK):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except Exception as e:
        print(f"  Warning: Could not fetch channel {channel_id}: {e}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        print(f"  Warning: XML parse error for {channel_id}: {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    videos = []

    for entry in root.findall("atom:entry", ns):
        video_id_elem = entry.find("yt:videoId", ns)
        title_elem = entry.find("atom:title", ns)
        published_elem = entry.find("atom:published", ns)

        if video_id_elem is None or title_elem is None:
            continue

        video_id = video_id_elem.text
        title = title_elem.text or ""
        published_str = published_elem.text if published_elem is not None else None

        if published_str:
            try:
                published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                if published < cutoff:
                    continue
            except ValueError:
                pass

        videos.append({
            "video_id": video_id,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "published": published_str,
        })

    return videos


def main():
    channels = load_channels()
    processed = load_processed()

    print(f"Loaded {len(processed)} already-processed video IDs.", file=sys.stderr)

    new_videos = []
    for channel in channels:
        channel_id = channel["channel_id"]
        channel_name = channel["name"]
        print(f"Checking: {channel_name} ({channel_id})", file=sys.stderr)

        videos = fetch_channel_videos(channel_id)
        for video in videos:
            if video["video_id"] not in processed:
                video["channel_name"] = channel_name
                new_videos.append(video)
                print(f"  + New: [{video['published']}] {video['title']}", file=sys.stderr)

    print(f"\nTotal new videos found: {len(new_videos)}", file=sys.stderr)
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
