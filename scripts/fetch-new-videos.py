#!/usr/bin/env python3
"""
한국 증시 유튜브 채널에서 새 영상을 확인하는 스크립트
YouTube RSS 피드를 사용하여 최신 영상을 가져옵니다.
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
from datetime import datetime, timezone, timedelta

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

# 최근 N일 이내 영상만 처리
DAYS_LOOKBACK = 3


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_rss(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        with urlopen(url, timeout=10) as resp:
            return resp.read()
    except URLError as e:
        print(f"  [오류] RSS 피드 요청 실패: {e}", file=sys.stderr)
        return None


def parse_rss(xml_bytes):
    """RSS XML에서 최근 영상 목록 반환"""
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(xml_bytes)
    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_LOOKBACK)

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)

        if video_id_el is None or title_el is None or published_el is None:
            continue

        video_id = video_id_el.text.strip()
        title = title_el.text.strip()
        published_str = published_el.text.strip()

        # ISO 8601 파싱
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if published >= cutoff:
            videos.append({
                "video_id": video_id,
                "title": title,
                "published": published_str,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })

    return videos


def main():
    channels = load_json(CHANNELS_FILE)["channels"]
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed_video_ids", []))

    new_videos = []

    for ch in channels:
        print(f"[채널] {ch['name']} ({ch['channel_id']}) 확인 중...", file=sys.stderr)
        xml_bytes = fetch_rss(ch["channel_id"])
        if xml_bytes is None:
            continue

        videos = parse_rss(xml_bytes)
        for v in videos:
            if v["video_id"] not in processed_ids:
                v["channel_name"] = ch["name"]
                new_videos.append(v)
                print(f"  [새 영상] {v['title']} ({v['video_id']})", file=sys.stderr)

    # 결과를 JSON으로 stdout 출력
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
