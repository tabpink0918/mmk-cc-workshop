#!/usr/bin/env python3
"""
한국 증시 유튜브 채널의 새 영상을 RSS 피드로 확인합니다.
새 영상(processed.json에 없는 것)만 출력합니다.
"""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS_FILE = os.path.join(BASE_DIR, "data", "channels.json")
PROCESSED_FILE = os.path.join(BASE_DIR, "data", "processed.json")

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
MAX_VIDEOS_PER_CHANNEL = 5


def load_channels():
    with open(CHANNELS_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def fetch_channel_videos(channel_id, channel_name):
    url = RSS_URL.format(channel_id=channel_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
    except Exception as e:
        print(f"⚠ [{channel_name}] RSS 가져오기 실패: {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"⚠ [{channel_name}] XML 파싱 실패: {e}", file=sys.stderr)
        return []

    videos = []
    for entry in root.findall("atom:entry", ns)[:MAX_VIDEOS_PER_CHANNEL]:
        vid_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        pub_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if vid_el is None or title_el is None:
            continue

        video_id = vid_el.text
        videos.append({
            "video_id": video_id,
            "title": title_el.text or "",
            "url": (link_el.get("href") if link_el is not None
                    else f"https://www.youtube.com/watch?v={video_id}"),
            "channel_name": channel_name,
            "published": pub_el.text if pub_el is not None else "",
        })
    return videos


def main():
    channels = load_channels()
    processed_ids = set(load_processed())

    new_videos = []
    for ch in channels:
        videos = fetch_channel_videos(ch["channel_id"], ch["name"])
        for v in videos:
            if v["video_id"] not in processed_ids:
                new_videos.append(v)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    print(f"\n총 {len(new_videos)}개의 새 영상 발견", file=sys.stderr)


if __name__ == "__main__":
    main()
