#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS."""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

NAMESPACE = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
MAX_VIDEOS_PER_CHANNEL = 3


def load_processed():
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text()))
    return set()


def load_channels():
    return json.loads(CHANNELS_FILE.read_text())


def fetch_channel_videos(channel_id: str, channel_name: str) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            xml_data = resp.read()
    except Exception as e:
        print(f"[ERROR] {channel_name} RSS fetch 실패: {e}", file=sys.stderr)
        return []

    root = ET.fromstring(xml_data)
    videos = []
    for entry in root.findall("atom:entry", NAMESPACE)[:MAX_VIDEOS_PER_CHANNEL]:
        video_id_el = entry.find("yt:videoId", NAMESPACE)
        title_el = entry.find("atom:title", NAMESPACE)
        if video_id_el is None or title_el is None:
            continue
        video_id = video_id_el.text
        title = title_el.text
        url = f"https://www.youtube.com/watch?v={video_id}"
        videos.append({"video_id": video_id, "title": title, "url": url, "channel": channel_name})
    return videos


def main():
    processed = load_processed()
    channels = load_channels()

    new_videos = []
    for ch in channels:
        videos = fetch_channel_videos(ch["channel_id"], ch["name"])
        for v in videos:
            if v["video_id"] not in processed:
                new_videos.append(v)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
