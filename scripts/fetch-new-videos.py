#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS feeds."""

import json
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "media": "http://search.yahoo.com/mrss/"}

# Only fetch videos published within the last 24 hours
MAX_AGE_HOURS = 24


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        print(f"  [warn] RSS fetch failed for {channel_id}: {e}", file=sys.stderr)
        return None


def parse_videos(xml_bytes, channel_name):
    root = ET.fromstring(xml_bytes)
    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    for entry in root.findall("atom:entry", NS):
        video_id = entry.findtext("yt:videoId", namespaces=NS)
        title = entry.findtext("atom:title", namespaces=NS)
        link_el = entry.find("atom:link[@rel='alternate']", NS)
        url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"
        published_str = entry.findtext("atom:published", namespaces=NS)
        if not video_id or not title:
            continue
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except Exception:
            published = datetime.now(timezone.utc)
        if published < cutoff:
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
    processed = set(load_json(PROCESSED_FILE))

    new_videos = []
    for ch in channels:
        print(f"Checking {ch['name']} ...", file=sys.stderr)
        xml_bytes = fetch_rss(ch["channel_id"])
        if xml_bytes is None:
            continue
        try:
            videos = parse_videos(xml_bytes, ch["name"])
        except ET.ParseError as e:
            print(f"  [warn] XML parse error for {ch['name']}: {e}", file=sys.stderr)
            continue
        for v in videos:
            if v["video_id"] not in processed:
                new_videos.append(v)
                print(f"  [new] {v['title']} ({v['video_id']})", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
