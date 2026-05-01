#!/usr/bin/env python3
"""
한국 증시 유튜브 채널 새 영상 감지 스크립트
YouTube RSS 피드를 사용하여 처리되지 않은 새 영상을 출력합니다.
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET

CHANNELS = [
    {"name": "삼프로TV 3PROTV",  "id": "UChlv4GSd7OQl3js-jkLOnFA"},
    {"name": "한국경제TV",        "id": "UCF8AeLlUbEpKju6v1H6p8Eg"},
    {"name": "슈카월드",          "id": "UCsJ6RuBiTVWRX156FVbeaGg"},
]

PROCESSED_FILE = "data/processed.json"
LOOKBACK_HOURS = 48
NS = {
    "atom":  "http://www.w3.org/2005/Atom",
    "yt":    "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def load_processed():
    try:
        with open(PROCESSED_FILE) as f:
            return set(json.load(f).get("processed_video_ids", []))
    except FileNotFoundError:
        return set()


def fetch_rss(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def parse_entries(xml_bytes, channel_name, cutoff):
    root = ET.fromstring(xml_bytes)
    videos = []
    for entry in root.findall("atom:entry", NS):
        vid_id    = entry.find("yt:videoId", NS).text
        title     = entry.find("atom:title", NS).text
        published = entry.find("atom:published", NS).text
        link      = entry.find("atom:link", NS).get("href")
        pub_dt    = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if pub_dt >= cutoff:
            videos.append({
                "video_id": vid_id,
                "title": title,
                "url": link,
                "published": published,
                "channel": channel_name,
            })
    return videos


def main():
    processed = load_processed()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    new_videos = []

    for ch in CHANNELS:
        try:
            xml_bytes = fetch_rss(ch["id"])
            entries = parse_entries(xml_bytes, ch["name"], cutoff)
            for v in entries:
                if v["video_id"] not in processed:
                    new_videos.append(v)
        except Exception as e:
            print(f"[WARN] {ch['name']} RSS 오류: {e}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0 if new_videos else 0


if __name__ == "__main__":
    sys.exit(main())
