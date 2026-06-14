#!/usr/bin/env python3
"""
한국 증시 YouTube 채널에서 새 영상을 확인하는 스크립트.
YouTube RSS 피드를 이용하여 각 채널의 최신 영상을 가져오고,
data/processed.json에 없는 영상을 새 영상으로 반환합니다.
"""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

# 최근 N일 이내 영상만 대상
RECENT_DAYS = 3


def load_processed() -> set:
    if not PROCESSED_FILE.exists():
        return set()
    data = json.loads(PROCESSED_FILE.read_text())
    return set(data.get("processed_video_ids", []))


def fetch_channel_videos(channel_id: str, channel_name: str) -> list[dict]:
    url = RSS_URL.format(channel_id=channel_id)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [경고] {channel_name} RSS 조회 실패: {e}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        print(f"  [경고] {channel_name} XML 파싱 실패: {e}", file=sys.stderr)
        return []

    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)

    for entry in root.findall("atom:entry", NS):
        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        link_el = entry.find("atom:link", NS)

        if video_id_el is None or title_el is None:
            continue

        video_id = video_id_el.text
        title = title_el.text or ""
        published_str = published_el.text if published_el is not None else ""
        url = link_el.get("href", f"https://www.youtube.com/watch?v={video_id}") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        # 날짜 파싱
        published_dt = None
        if published_str:
            try:
                published_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        if published_dt and published_dt < cutoff:
            continue

        videos.append({
            "video_id": video_id,
            "title": title,
            "url": url,
            "published": published_str,
            "channel_name": channel_name,
        })

    return videos


def main():
    channels = json.loads(CHANNELS_FILE.read_text())
    processed = load_processed()

    all_new_videos = []

    for ch in channels:
        channel_id = ch["channel_id"]
        channel_name = ch["name"]
        print(f"채널 확인 중: {channel_name}", file=sys.stderr)
        videos = fetch_channel_videos(channel_id, channel_name)
        new_videos = [v for v in videos if v["video_id"] not in processed]
        print(f"  → 최근 {RECENT_DAYS}일 영상 {len(videos)}개, 미처리 {len(new_videos)}개", file=sys.stderr)
        all_new_videos.extend(new_videos)

    # JSON으로 출력 (부모 프로세스/Claude가 파싱)
    print(json.dumps(all_new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
