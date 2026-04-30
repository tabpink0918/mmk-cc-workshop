#!/usr/bin/env python3
"""
Fetch new videos from Korean stock market YouTube channels.
Reads data/channels.json for channel list and data/processed.json to skip already-processed videos.
Outputs new videos as JSON to stdout.
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
SSL_CA = "/etc/ssl/certs/ca-certificates.crt"

def load_json(path):
    with open(path) as f:
        return json.load(f)

def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; FeedFetcher)"}, verify=SSL_CA, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[warn] RSS fetch failed for {channel_id}: {e}", file=sys.stderr)
        return None

def parse_videos(rss_xml):
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(rss_xml)
    videos = []
    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        if video_id_el is None:
            continue
        vid_id = video_id_el.text
        title = title_el.text if title_el is not None else ""
        published = published_el.text if published_el is not None else ""
        videos.append({
            "video_id": vid_id,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "published": published,
        })
    return videos

def main():
    channels = load_json(CHANNELS_FILE)["channels"]
    processed = set(load_json(PROCESSED_FILE)["processed"])

    new_videos = []
    for ch in channels:
        rss_xml = fetch_rss(ch["channel_id"])
        if not rss_xml:
            continue
        videos = parse_videos(rss_xml)
        for v in videos:
            if v["video_id"] not in processed:
                v["channel"] = ch["name"]
                new_videos.append(v)
                print(f"[new] {ch['name']}: {v['title'][:60]} ({v['video_id']})", file=sys.stderr)

    if not new_videos:
        print("[info] No new videos found.", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
