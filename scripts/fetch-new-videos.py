#!/usr/bin/env python3
"""
Fetch new YouTube videos from Korean stock market channels.
Checks YouTube RSS feeds and filters out already-processed videos.
Outputs JSON array of new video objects to stdout.
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

NS = {
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
}


def load_processed():
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text())["processed"])
    return set()


def fetch_channel_videos(channel_id, channel_name, max_videos=5):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        xml_data = urllib.request.urlopen(req, timeout=15).read()
        root = ET.fromstring(xml_data)
        videos = []
        for entry in root.findall("atom:entry", NS)[:max_videos]:
            vid_id_el = entry.find("yt:videoId", NS)
            title_el = entry.find("atom:title", NS)
            published_el = entry.find("atom:published", NS)
            if vid_id_el is None or title_el is None:
                continue
            video_url = f"https://www.youtube.com/watch?v={vid_id_el.text}"
            videos.append({
                "video_id": vid_id_el.text,
                "title": title_el.text,
                "published": published_el.text[:10] if published_el is not None else "",
                "url": video_url,
                "channel": channel_name,
            })
        return videos
    except Exception as e:
        print(f"[경고] {channel_name} RSS 조회 실패: {e}", file=sys.stderr)
        return []


def main():
    channels_data = json.loads(CHANNELS_FILE.read_text())
    processed = load_processed()

    new_videos = []
    for ch in channels_data["channels"]:
        videos = fetch_channel_videos(ch["channel_id"], ch["name"])
        for v in videos:
            if v["video_id"] not in processed:
                new_videos.append(v)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))

    if new_videos:
        print(f"\n[결과] 새 영상 {len(new_videos)}개 발견", file=sys.stderr)
    else:
        print("[결과] 새 영상 없음", file=sys.stderr)


if __name__ == "__main__":
    main()
