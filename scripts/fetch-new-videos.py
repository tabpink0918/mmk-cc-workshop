#!/usr/bin/env python3
"""
Fetches new videos from Korean stock market YouTube channels via RSS feed.
Outputs JSON list of new (unprocessed) videos.
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

NS = {"atom": "http://www.w3.org/2005/Atom",
      "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def parse_videos(xml_bytes):
    root = ET.fromstring(xml_bytes)
    videos = []
    for entry in root.findall("atom:entry", NS):
        video_id = entry.findtext("yt:videoId", namespaces=NS)
        title = entry.findtext("atom:title", namespaces=NS)
        published = entry.findtext("atom:published", namespaces=NS)
        link_el = entry.find("atom:link", NS)
        url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"
        videos.append({
            "video_id": video_id,
            "title": title,
            "published": published,
            "url": url,
        })
    return videos


def main():
    channels = load_json(CHANNELS_FILE)["channels"]
    processed_ids = set(load_json(PROCESSED_FILE)["processed"])

    # Only consider videos published within the last 7 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    max_per_channel = 3  # process at most 3 long-form videos per channel

    new_videos = []
    for ch in channels:
        channel_id = ch["channel_id"]
        channel_name = ch["name"]
        print(f"[fetch] {channel_name} ({channel_id})", file=sys.stderr)
        try:
            xml_bytes = fetch_rss(channel_id)
            videos = parse_videos(xml_bytes)
            count = 0
            for v in videos:
                if v["video_id"] in processed_ids:
                    continue
                published = datetime.fromisoformat(v["published"])
                if published < cutoff:
                    continue
                if "/shorts/" in v["url"]:
                    continue
                if count >= max_per_channel:
                    break
                v["channel_name"] = channel_name
                new_videos.append(v)
                count += 1
        except Exception as e:
            print(f"[warn] {channel_name}: {e}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
