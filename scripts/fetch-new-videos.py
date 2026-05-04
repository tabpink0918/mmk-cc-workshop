#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS feed."""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_channel_videos(channel_id: str, channel_name: str) -> list[dict]:
    url = RSS_URL.format(channel_id=channel_id)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[WARN] {channel_name} RSS 조회 실패: {e}", file=sys.stderr)
        return []

    root = ET.fromstring(resp.text)
    videos = []
    for entry in root.findall("atom:entry", NS):
        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        if video_id_el is None or title_el is None:
            continue
        videos.append({
            "video_id": video_id_el.text,
            "title": title_el.text,
            "url": f"https://www.youtube.com/watch?v={video_id_el.text}",
            "published": published_el.text if published_el is not None else "",
            "channel": channel_name,
        })
    return videos


def main():
    channels_data = load_json(CHANNELS_FILE)
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed_video_ids", []))

    new_videos = []
    for ch in channels_data["channels"]:
        videos = fetch_channel_videos(ch["channel_id"], ch["name"])
        for v in videos:
            if v["video_id"] not in processed_ids:
                new_videos.append(v)

    if not new_videos:
        print("새 영상 없음")
        print(json.dumps([], ensure_ascii=False))
        return

    print(f"새 영상 {len(new_videos)}개 발견", file=sys.stderr)
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
