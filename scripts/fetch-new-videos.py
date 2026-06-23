#!/usr/bin/env python3
"""
Fetch new videos from Korean stock market YouTube channels.
Compares against data/processed.json to find unprocessed videos.
Outputs JSON with new video info to stdout.
"""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

NS_ATOM = "{http://www.w3.org/2005/Atom}"
NS_YT = "{http://www.youtube.com/xml/schemas/2015}"
NS_MEDIA = "{http://search.yahoo.com/mrss/}"

# Only surface videos published within the last 2 days
LOOKBACK_HOURS = 48


def load_json(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def fetch_rss(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return ET.fromstring(r.content)


def parse_entries(root, channel_name):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    videos = []
    for entry in root.findall(f"{NS_ATOM}entry"):
        vid_id = entry.find(f"{NS_YT}videoId")
        title = entry.find(f"{NS_ATOM}title")
        published = entry.find(f"{NS_ATOM}published")
        link = entry.find(f"{NS_ATOM}link")

        if vid_id is None or title is None or published is None:
            continue

        pub_dt = datetime.fromisoformat(published.text.replace("Z", "+00:00"))
        if pub_dt < cutoff:
            continue

        url = link.get("href") if link is not None else f"https://www.youtube.com/watch?v={vid_id.text}"
        videos.append({
            "video_id": vid_id.text,
            "title": title.text,
            "published": published.text,
            "url": url,
            "channel": channel_name,
        })
    return videos


def main():
    channels_data = load_json(CHANNELS_FILE)
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed_ids", []))

    new_videos = []
    errors = []

    for ch in channels_data.get("channels", []):
        name = ch["name"]
        cid = ch["channel_id"]
        try:
            root = fetch_rss(cid)
            videos = parse_entries(root, name)
            for v in videos:
                if v["video_id"] not in processed_ids:
                    new_videos.append(v)
            print(f"[{name}] {len(videos)} recent, {sum(1 for v in videos if v['video_id'] not in processed_ids)} new", file=sys.stderr)
        except Exception as e:
            errors.append({"channel": name, "error": str(e)})
            print(f"[{name}] ERROR: {e}", file=sys.stderr)

    result = {"new_videos": new_videos, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
