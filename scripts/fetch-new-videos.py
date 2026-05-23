#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS."""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"
PROCESSED_FILE = DATA_DIR / "processed.json"

# Only consider videos published within the last N days
LOOKBACK_DAYS = 3


def load_json(path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def fetch_rss(channel_id: str) -> bytes | None:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as e:
        print(f"  Warning: failed to fetch RSS for {channel_id}: {e}", file=sys.stderr)
        return None


def parse_feed(xml_data: bytes) -> list[dict]:
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    root = ET.fromstring(xml_data)
    videos = []
    for entry in root.findall("atom:entry", ns):
        vid_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)
        if vid_el is None:
            continue
        video_id = vid_el.text
        videos.append({
            "video_id": video_id,
            "title": title_el.text if title_el is not None else "",
            "published": published_el.text if published_el is not None else "",
            "url": (link_el.get("href") if link_el is not None
                    else f"https://www.youtube.com/watch?v={video_id}"),
        })
    return videos


def main():
    channels = load_json(CHANNELS_FILE, [])
    processed = load_json(PROCESSED_FILE, {"processed": []})
    processed_ids = set(processed.get("processed", []))

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    new_videos = []

    for ch in channels:
        channel_id = ch["channel_id"]
        channel_name = ch["name"]
        print(f"Checking: {channel_name}", file=sys.stderr)

        xml_data = fetch_rss(channel_id)
        if xml_data is None:
            continue

        for v in parse_feed(xml_data):
            if v["video_id"] in processed_ids:
                continue
            try:
                pub = datetime.fromisoformat(v["published"].replace("Z", "+00:00"))
                if pub < cutoff:
                    continue
            except Exception:
                pass
            v["channel_name"] = channel_name
            v["channel_id"] = channel_id
            new_videos.append(v)
            print(f"  NEW: [{v['published'][:10]}] {v['title']}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    print(f"\nTotal new videos: {len(new_videos)}", file=sys.stderr)


if __name__ == "__main__":
    main()
