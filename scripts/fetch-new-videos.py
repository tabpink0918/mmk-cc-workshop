#!/usr/bin/env python3
"""
Fetch new videos from Korean stock market YouTube channels.
Compares against data/processed.json and returns videos published in the last 24h.
Outputs JSON to stdout.
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
VIDEO_URL = "https://www.youtube.com/watch?v={video_id}"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

LOOKBACK_HOURS = 24


def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def parse_feed(xml_text, channel_name):
    root = ET.fromstring(xml_text)
    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    for entry in root.findall("atom:entry", NS):
        vid_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        link_el = entry.find("atom:link", NS)

        if vid_id_el is None or title_el is None or published_el is None:
            continue

        video_id = vid_id_el.text
        title = title_el.text
        published_str = published_el.text
        url = link_el.get("href") if link_el is not None else VIDEO_URL.format(video_id=video_id)

        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except Exception:
            continue

        if published >= cutoff:
            videos.append({
                "video_id": video_id,
                "title": title,
                "url": url,
                "published": published_str,
                "channel": channel_name,
            })

    return videos


def main():
    channels = load_json(CHANNELS_FILE)
    processed_ids = set(load_json(PROCESSED_FILE))

    new_videos = []

    for ch in channels:
        name = ch["name"]
        channel_id = ch["channel_id"]
        print(f"Checking {name}...", file=sys.stderr)

        xml_text = fetch_rss(channel_id)
        if not xml_text:
            continue

        try:
            videos = parse_feed(xml_text, name)
        except Exception as e:
            print(f"  [WARN] Parse error for {name}: {e}", file=sys.stderr)
            continue

        for v in videos:
            if v["video_id"] not in processed_ids:
                new_videos.append(v)
                print(f"  [NEW] {v['title'][:60]} ({v['published']})", file=sys.stderr)
            else:
                print(f"  [SKIP] Already processed: {v['video_id']}", file=sys.stderr)

    print(f"\nTotal new videos: {len(new_videos)}", file=sys.stderr)
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
