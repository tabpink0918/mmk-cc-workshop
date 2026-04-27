#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS feeds."""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
# Look back 7 days for new videos
LOOKBACK_DAYS = 7


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read()
    except Exception as e:
        print(f"  [WARN] RSS fetch failed for {channel_id}: {e}", file=sys.stderr)
        return None


def parse_rss(xml_data):
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(xml_data)
    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if video_id_el is None or title_el is None:
            continue

        video_id = video_id_el.text
        title = title_el.text
        published_str = published_el.text if published_el is not None else None
        url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        # Filter by recency
        if published_str:
            try:
                published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                if published < cutoff:
                    continue
            except ValueError:
                pass

        videos.append({"video_id": video_id, "title": title, "url": url, "published": published_str})

    return videos


def main():
    channels = load_json(CHANNELS_FILE)["channels"]
    processed_ids = set(load_json(PROCESSED_FILE)["processed"])

    new_videos = []

    for channel in channels:
        name = channel["name"]
        channel_id = channel["channel_id"]
        print(f"Checking {name} ({channel_id})...", file=sys.stderr)

        xml_data = fetch_rss(channel_id)
        if not xml_data:
            continue

        videos = parse_rss(xml_data)
        for video in videos:
            if video["video_id"] not in processed_ids:
                video["channel_name"] = name
                new_videos.append(video)
                print(f"  [NEW] {video['title']} ({video['video_id']})", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
