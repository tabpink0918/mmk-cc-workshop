#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS."""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS_FILE = os.path.join(BASE_DIR, "data", "channels.json")
PROCESSED_FILE = os.path.join(BASE_DIR, "data", "processed.json")
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

# Only include videos published within the last 48 hours
LOOKBACK_HOURS = 48


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def fetch_channel_videos(channel_id, channel_name, max_videos=10):
    url = RSS_URL.format(channel_id=channel_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
    except Exception as e:
        print(f"[WARN] {channel_name} 채널 RSS 가져오기 실패: {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"[WARN] {channel_name} RSS 파싱 실패: {e}", file=sys.stderr)
        return []

    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    for entry in root.findall("atom:entry", ns)[:max_videos]:
        try:
            video_id = entry.find("yt:videoId", ns).text
            title = entry.find("atom:title", ns).text
            link = entry.find("atom:link", ns).get("href")
            published_str = entry.find("atom:published", ns).text
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

            if published < cutoff:
                continue

            videos.append({
                "video_id": video_id,
                "title": title,
                "url": link,
                "published": published_str,
                "channel_name": channel_name,
            })
        except Exception:
            continue

    return videos


def main():
    channels = load_json(CHANNELS_FILE, [])
    processed = set(load_json(PROCESSED_FILE, []))
    new_videos = []

    for ch in channels:
        videos = fetch_channel_videos(ch["channel_id"], ch["name"])
        for v in videos:
            if v["video_id"] not in processed:
                new_videos.append(v)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
