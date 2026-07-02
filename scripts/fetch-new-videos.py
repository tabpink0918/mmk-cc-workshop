#!/usr/bin/env python3
"""한국 증시 유튜브 채널에서 최신 영상을 가져와 미처리 영상을 출력합니다."""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as e:
        print(f"[WARN] RSS 요청 실패 ({channel_id}): {e}", file=sys.stderr)
        return None


def parse_rss(xml_bytes, channel_name):
    videos = []
    try:
        root = ET.fromstring(xml_bytes)
        for entry in root.findall("atom:entry", NS):
            video_id_el = entry.find("yt:videoId", NS)
            title_el = entry.find("atom:title", NS)
            link_el = entry.find("atom:link", NS)
            published_el = entry.find("atom:published", NS)
            if video_id_el is None or title_el is None:
                continue
            videos.append({
                "video_id": video_id_el.text,
                "title": title_el.text,
                "url": link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id_el.text}",
                "published": published_el.text if published_el is not None else "",
                "channel": channel_name,
            })
    except ET.ParseError as e:
        print(f"[WARN] XML 파싱 실패: {e}", file=sys.stderr)
    return videos


def main():
    channels = load_json(CHANNELS_FILE)["channels"]
    processed_ids = set(load_json(PROCESSED_FILE).get("processed_video_ids", []))

    new_videos = []
    for ch in channels:
        xml_bytes = fetch_rss(ch["channel_id"])
        if xml_bytes is None:
            continue
        videos = parse_rss(xml_bytes, ch["name"])
        # 최신 3개만 확인 (과거 영상 대량 처리 방지)
        for v in videos[:3]:
            if v["video_id"] not in processed_ids:
                new_videos.append(v)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return len(new_videos)


if __name__ == "__main__":
    count = main()
    sys.exit(0 if count >= 0 else 1)
