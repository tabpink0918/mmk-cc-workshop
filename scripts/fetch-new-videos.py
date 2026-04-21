#!/usr/bin/env python3
"""
한국 증시 YouTube 채널에서 새 영상을 확인하는 스크립트.
RSS 피드를 사용하여 API 키 없이 최신 영상을 가져옵니다.
"""
import json
import os
import sys
import xml.etree.ElementTree as ET
import urllib.request

CHANNELS = [
    {"name": "삼프로TV", "channel_id": "UChlv4GSd7OQl3js-jkLOnFA"},
    {"name": "슈카월드", "channel_id": "UCsJ6RuBiTVWRX156FVbeaGg"},
    {"name": "한국경제TV", "channel_id": "UCF8AeLlUbEpKju6v1H6p8Eg"},
]

PROCESSED_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "processed.json")
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def load_processed():
    path = os.path.normpath(PROCESSED_FILE)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"processed_video_ids": []}


def fetch_channel_videos(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read()
    except Exception as e:
        print(f"  채널 {channel_id} 조회 실패: {e}", file=sys.stderr)
        return None


def parse_videos(xml_content):
    try:
        root = ET.fromstring(xml_content)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        videos = []
        for entry in root.findall("atom:entry", ns):
            video_id_el = entry.find("yt:videoId", ns)
            title_el = entry.find("atom:title", ns)
            published_el = entry.find("atom:published", ns)
            if video_id_el is not None and title_el is not None:
                videos.append({
                    "video_id": video_id_el.text,
                    "title": title_el.text,
                    "url": f"https://www.youtube.com/watch?v={video_id_el.text}",
                    "published": published_el.text if published_el is not None else "",
                })
        return videos
    except Exception as e:
        print(f"  XML 파싱 실패: {e}", file=sys.stderr)
        return []


def main():
    processed = load_processed()
    processed_ids = set(processed.get("processed_video_ids", []))

    new_videos = []

    for channel in CHANNELS:
        print(f"확인 중: {channel['name']} ...", file=sys.stderr)
        xml_content = fetch_channel_videos(channel["channel_id"])
        if xml_content is None:
            continue
        videos = parse_videos(xml_content)
        for video in videos[:3]:  # 최신 3개만 확인
            if video["video_id"] not in processed_ids:
                video["channel"] = channel["name"]
                new_videos.append(video)

    print(f"\n새 영상: {len(new_videos)}개", file=sys.stderr)
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
