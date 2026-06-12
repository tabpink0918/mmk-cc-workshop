#!/usr/bin/env python3
"""
Fetch new videos from Korean stock market YouTube channels.
Checks for recent uploads and filters out already-processed videos.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Korean stock market YouTube channels
CHANNELS = [
    {"name": "삼프로TV", "channel_id": "UCuEDIkO5NWzMZZoLFYf0BPQ", "handle": "@3protv"},
    {"name": "한국경제TV", "channel_id": "UCcQTRi69dsVYHN3exePtZ1A", "handle": "@한국경제TV"},
    {"name": "머니투데이방송", "channel_id": "UCIkNOrBElGm8fwJpUZ3sSFA", "handle": "@MTN"},
]

# Representative recent video URLs per channel to check
# These are well-known channels; we fetch their latest videos via metadata
CHANNEL_LATEST_URLS = [
    # 삼프로TV recent videos
    "https://www.youtube.com/@3protv/videos",
    # We'll use known recent video IDs from these channels
]

PROCESSED_FILE = Path(__file__).parent.parent / "data" / "processed.json"


def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            data = json.load(f)
            return set(data.get("processed", []))
    return set()


def get_channel_recent_videos():
    """
    Returns a list of recent video dicts with url, title, channel_name.
    Uses known recent video URLs from major Korean stock channels.
    """
    # These are recent videos from major Korean stock market channels
    # In production, this would use YouTube Data API or RSS feeds
    candidate_videos = [
        {
            "video_id": "dQw4w9WgXcQ",  # placeholder - will be replaced by real IDs
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "channel_name": "샘플",
            "title": "샘플 영상",
        }
    ]

    # Try to get real recent videos from Korean stock channels via RSS
    import urllib.request
    import xml.etree.ElementTree as ET

    real_videos = []
    rss_channels = [
        ("삼프로TV", "UCuEDIkO5NWzMZZoLFYf0BPQ"),
        ("한국경제TV", "UCcQTRi69dsVYHN3exePtZ1A"),
        ("머니투데이방송", "UCIkNOrBElGm8fwJpUZ3sSFA"),
    ]

    for channel_name, channel_id in rss_channels:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read()
            root = ET.fromstring(content)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "yt": "http://www.youtube.com/xml/schemas/2015",
                "media": "http://search.yahoo.com/mrss/",
            }
            entries = root.findall("atom:entry", ns)
            for entry in entries[:3]:  # Latest 3 videos
                video_id_el = entry.find("yt:videoId", ns)
                title_el = entry.find("atom:title", ns)
                published_el = entry.find("atom:published", ns)
                if video_id_el is not None and title_el is not None:
                    video_id = video_id_el.text
                    title = title_el.text
                    published = published_el.text if published_el is not None else ""
                    real_videos.append({
                        "video_id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "channel_name": channel_name,
                        "title": title,
                        "published": published,
                    })
        except Exception as e:
            print(f"[WARN] {channel_name} RSS fetch failed: {e}", file=sys.stderr)

    return real_videos


def main():
    processed = load_processed()
    all_videos = get_channel_recent_videos()

    new_videos = [v for v in all_videos if v["video_id"] not in processed]

    print(json.dumps({
        "total_fetched": len(all_videos),
        "new_videos": new_videos,
        "already_processed": len(processed),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
