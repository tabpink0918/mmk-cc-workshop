#!/usr/bin/env python3
"""
YouTube RSS 피드에서 신규 영상을 가져와 키워드 필터링 후 JSON 출력.

사용법:
  python3 scripts/fetch_videos.py
  python3 scripts/fetch_videos.py --all   # 처리 완료 영상도 포함해서 출력
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "channels.json")
PROCESSED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed_videos.json")

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
YOUTUBE_URL = "https://www.youtube.com/watch?v={video_id}"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_processed():
    if not os.path.exists(PROCESSED_PATH):
        return {}
    with open(PROCESSED_PATH, encoding="utf-8") as f:
        return json.load(f)


def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def parse_rss(xml_bytes, channel_name, keywords):
    root = ET.fromstring(xml_bytes)
    videos = []
    for entry in root.findall("atom:entry", NS):
        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)

        if video_id_el is None or title_el is None:
            continue

        video_id = video_id_el.text.strip()
        title = title_el.text.strip()
        published = published_el.text.strip() if published_el is not None else ""

        # 키워드 필터링 (제목에 하나라도 포함)
        if not any(kw in title for kw in keywords):
            continue

        videos.append({
            "video_id": video_id,
            "title": title,
            "url": YOUTUBE_URL.format(video_id=video_id),
            "channel": channel_name,
            "published": published,
        })
    return videos


def main():
    show_all = "--all" in sys.argv

    config = load_config()
    processed = load_processed()

    new_videos = []
    errors = []

    for ch in config["channels"]:
        try:
            xml_bytes = fetch_rss(ch["channel_id"])
            videos = parse_rss(xml_bytes, ch["name"], ch["keywords"])
            for v in videos:
                if show_all or v["video_id"] not in processed:
                    new_videos.append(v)
        except Exception as e:
            errors.append({"channel": ch["name"], "error": str(e)})

    result = {
        "new_videos": new_videos,
        "count": len(new_videos),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
