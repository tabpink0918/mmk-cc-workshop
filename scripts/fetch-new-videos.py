#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS."""
import json
import os
import sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS_FILE = os.path.join(BASE_DIR, "data", "channels.json")
PROCESSED_FILE = os.path.join(BASE_DIR, "data", "processed.json")

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_channel_videos(channel_id, max_age_hours=48):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"  [WARN] {channel_id}: HTTP {resp.status_code}", file=sys.stderr)
            return []
        root = ET.fromstring(resp.content)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        videos = []
        for entry in root.findall("atom:entry", NS):
            vid_el = entry.find("yt:videoId", NS)
            title_el = entry.find("atom:title", NS)
            pub_el = entry.find("atom:published", NS)
            if vid_el is None or title_el is None or pub_el is None:
                continue
            pub_dt = datetime.fromisoformat(pub_el.text.replace("Z", "+00:00"))
            if pub_dt >= cutoff:
                videos.append({
                    "video_id": vid_el.text,
                    "title": title_el.text,
                    "url": f"https://www.youtube.com/watch?v={vid_el.text}",
                    "published": pub_el.text,
                    "channel_id": channel_id,
                })
        return videos
    except Exception as e:
        print(f"  [ERROR] {channel_id}: {e}", file=sys.stderr)
        return []


def main():
    channels = load_json(CHANNELS_FILE, [])
    processed = load_json(PROCESSED_FILE, {"processed": []})
    processed_ids = set(processed.get("processed", []))

    new_videos = []
    for ch in channels:
        cid = ch["channel_id"]
        name = ch.get("name", cid)
        print(f"Checking {name} ...", file=sys.stderr)
        videos = fetch_channel_videos(cid)
        for v in videos:
            if v["video_id"] not in processed_ids:
                v["channel_name"] = name
                new_videos.append(v)
        print(f"  {len(videos)} recent, {sum(1 for v in videos if v['video_id'] not in processed_ids)} new", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
