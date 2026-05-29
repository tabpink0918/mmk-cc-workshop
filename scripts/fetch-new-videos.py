#!/usr/bin/env python3
"""YouTube 채널에서 새 영상을 가져오는 스크립트 (RSS 피드 기반)"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"
PROCESSED_FILE = DATA_DIR / "processed.json"

NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

def fetch_channel_videos(channel_id: str, max_results: int = 5) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            xml_data = resp.read()
    except Exception as e:
        print(f"  RSS 피드 오류 (channel_id={channel_id}): {e}", file=sys.stderr)
        return []

    root = ET.fromstring(xml_data)
    videos = []
    for entry in root.findall("atom:entry", NS)[:max_results]:
        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        if video_id_el is None:
            continue
        vid = video_id_el.text
        videos.append({
            "video_id": vid,
            "title": title_el.text if title_el is not None else "",
            "published": published_el.text if published_el is not None else "",
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
    return videos


def main():
    channels = json.loads(CHANNELS_FILE.read_text())
    processed = json.loads(PROCESSED_FILE.read_text())
    processed_ids = set(processed.get("processed_video_ids", []))

    new_videos = []
    for ch in channels:
        print(f"채널 확인 중: {ch['name']} ...", file=sys.stderr)
        videos = fetch_channel_videos(ch["channel_id"])
        for v in videos:
            if v["video_id"] not in processed_ids:
                v["channel_name"] = ch["name"]
                new_videos.append(v)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    print(f"\n새 영상 {len(new_videos)}개 발견", file=sys.stderr)


if __name__ == "__main__":
    main()
