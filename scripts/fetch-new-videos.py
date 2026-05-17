#!/usr/bin/env python3
"""Fetch new YouTube videos from monitored Korean stock market channels.

Reads channels from data/channels.json, compares against data/processed.json,
and outputs new videos (from last LOOKBACK_DAYS) as JSON to stdout.
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

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}

LOOKBACK_DAYS = 7


def load_channels():
    with open(CHANNELS_FILE) as f:
        return json.load(f)["channels"]


def load_processed():
    if not PROCESSED_FILE.exists():
        return set()
    with open(PROCESSED_FILE) as f:
        data = json.load(f)
        return set(data.get("processed", []))


def fetch_rss(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode()


def parse_rss(xml_data, channel_name, processed_ids, cutoff):
    root = ET.fromstring(xml_data)
    entries = root.findall("atom:entry", NS)
    new_videos = []
    for entry in entries:
        vid_id = entry.find("yt:videoId", NS).text
        if vid_id in processed_ids:
            continue
        published_str = entry.find("atom:published", NS).text
        published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        if published < cutoff:
            continue
        title = entry.find("atom:title", NS).text
        link_elem = entry.find("atom:link", NS)
        url = link_elem.attrib.get("href", f"https://www.youtube.com/watch?v={vid_id}")
        new_videos.append({
            "video_id": vid_id,
            "title": title,
            "published": published_str[:10],
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "channel": channel_name,
        })
    return new_videos


def main():
    channels = load_channels()
    processed = load_processed()
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    all_new = []
    for ch in channels:
        try:
            xml_data = fetch_rss(ch["channel_id"])
            new = parse_rss(xml_data, ch["name"], processed, cutoff)
            all_new.extend(new)
            print(f"[{ch['name']}] 새 영상 {len(new)}개 발견", file=sys.stderr)
        except Exception as e:
            print(f"[{ch['name']}] 오류: {e}", file=sys.stderr)

    if not all_new:
        print("새 영상 없음", file=sys.stderr)
    else:
        print(f"총 {len(all_new)}개 새 영상 발견", file=sys.stderr)

    print(json.dumps(all_new, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
