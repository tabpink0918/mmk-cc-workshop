#!/usr/bin/env python3
"""Fetch new YouTube videos from Korean stock market channels via RSS feeds."""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS_FILE = os.path.join(BASE_DIR, "data", "channels.json")
PROCESSED_FILE = os.path.join(BASE_DIR, "data", "processed.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def resolve_channel_id(channel_url: str) -> str | None:
    """Fetch YouTube channel page and extract the channel ID."""
    patterns = [
        r'channel_id=(UC[a-zA-Z0-9_-]+)',
        r'"channelId":"(UC[a-zA-Z0-9_-]+)"',
        r'"externalChannelId":"(UC[a-zA-Z0-9_-]+)"',
        r'/channel/(UC[a-zA-Z0-9_-]+)',
    ]
    try:
        resp = requests.get(channel_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        for pattern in patterns:
            match = re.search(pattern, resp.text)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"  [warn] Could not resolve channel ID for {channel_url}: {e}", file=sys.stderr)
    return None


def fetch_rss(channel_id: str) -> list[dict]:
    """Fetch and parse YouTube RSS feed for a channel."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }

    videos = []
    for entry in root.findall("atom:entry", ns):
        vid_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        pub_el = entry.find("atom:published", ns)
        if vid_el is None or title_el is None or pub_el is None:
            continue
        videos.append(
            {
                "video_id": vid_el.text,
                "title": title_el.text,
                "published": pub_el.text,
                "url": f"https://www.youtube.com/watch?v={vid_el.text}",
            }
        )
    return videos


def load_processed() -> set:
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def load_channels() -> list[dict]:
    with open(CHANNELS_FILE) as f:
        return json.load(f)


def get_new_videos(hours: int = 48) -> list[dict]:
    processed = load_processed()
    channels = load_channels()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    new_videos = []

    for ch in channels:
        name = ch.get("name", ch.get("url", "unknown"))
        print(f"Checking: {name}", file=sys.stderr)

        channel_id = ch.get("channel_id")
        if not channel_id:
            channel_id = resolve_channel_id(ch["url"])

        if not channel_id:
            print(f"  [skip] Could not get channel ID", file=sys.stderr)
            continue

        try:
            videos = fetch_rss(channel_id)
        except Exception as e:
            print(f"  [skip] RSS error: {e}", file=sys.stderr)
            continue

        for v in videos:
            if v["video_id"] in processed:
                continue
            pub_dt = datetime.fromisoformat(v["published"].replace("Z", "+00:00"))
            if pub_dt >= cutoff:
                v["channel_name"] = name
                new_videos.append(v)
                print(f"  New: {v['title']}", file=sys.stderr)

    return new_videos


if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    videos = get_new_videos(hours=hours)
    if not videos:
        print(json.dumps([], ensure_ascii=False))
    else:
        print(json.dumps(videos, ensure_ascii=False, indent=2))
