#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS feeds."""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone, timedelta

import requests

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
# Check videos published within the last 48 hours
LOOKBACK_HOURS = 48


def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def fetch_channel_videos(channel_id, channel_name):
    url = RSS_URL.format(channel_id=channel_id)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[WARN] {channel_name} RSS 조회 실패: {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        print(f"[WARN] {channel_name} XML 파싱 실패: {e}", file=sys.stderr)
        return []

    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if video_id_el is None or title_el is None:
            continue

        video_id = video_id_el.text
        title = title_el.text or ""
        url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"
        published_str = published_el.text if published_el is not None else ""

        published_dt = None
        if published_str:
            try:
                published_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Skip videos older than lookback window
        if published_dt and published_dt < cutoff:
            continue

        videos.append({
            "video_id": video_id,
            "title": title,
            "url": url,
            "channel": channel_name,
            "published": published_str,
        })

    return videos


def main():
    channels = load_json(CHANNELS_FILE)
    processed_ids = set(load_json(PROCESSED_FILE))

    new_videos = []
    for ch in channels:
        videos = fetch_channel_videos(ch["channel_id"], ch["name"])
        for v in videos:
            if v["video_id"] not in processed_ids:
                new_videos.append(v)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0 if new_videos else 0


if __name__ == "__main__":
    sys.exit(main())
