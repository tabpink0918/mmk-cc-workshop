#!/usr/bin/env python3
"""
Fetch new YouTube videos from Korean stock market channels.
Compares against data/processed.json to find unprocessed videos.
Outputs new video info as JSON to stdout.
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

# Only consider videos published within the last 48 hours
MAX_AGE_HOURS = 48

def load_channels():
    with open(CHANNELS_FILE) as f:
        return json.load(f)["channels"]

def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            data = json.load(f)
            return set(data.get("processed_video_ids", []))
    return set()

def fetch_channel_videos(channel_id, channel_name):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
        root = ET.fromstring(content)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "media": "http://search.yahoo.com/mrss/",
        }
        videos = []
        for entry in root.findall("atom:entry", ns):
            video_id_el = entry.find("yt:videoId", ns)
            title_el = entry.find("atom:title", ns)
            published_el = entry.find("atom:published", ns)
            link_el = entry.find("atom:link", ns)
            if video_id_el is None or title_el is None:
                continue
            video_id = video_id_el.text
            title = title_el.text
            published = published_el.text if published_el is not None else ""
            url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"
            videos.append({
                "video_id": video_id,
                "title": title,
                "published": published,
                "url": url,
                "channel": channel_name,
            })
        return videos
    except Exception as e:
        print(f"[warn] Failed to fetch {channel_name} ({channel_id}): {e}", file=sys.stderr)
        return []

def is_recent(published_str):
    if not published_str:
        return True
    try:
        # Parse ISO 8601
        dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
        return dt >= cutoff
    except Exception:
        return True

def main():
    channels = load_channels()
    processed = load_processed()

    new_videos = []
    for ch in channels:
        videos = fetch_channel_videos(ch["channel_id"], ch["name"])
        for v in videos:
            if v["video_id"] not in processed and is_recent(v["published"]):
                new_videos.append(v)

    print(json.dumps({"new_videos": new_videos, "count": len(new_videos)}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
