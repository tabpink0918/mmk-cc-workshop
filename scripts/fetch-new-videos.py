#!/usr/bin/env python3
"""
한국 증시 유튜브 채널에서 새 영상을 확인합니다.
YouTube RSS 피드를 사용하여 최신 영상을 가져옵니다.
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

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
# 최근 N일 이내의 영상만 확인
DAYS_LOOKBACK = 3


def fetch_rss(channel_id: str) -> list[dict]:
    url = RSS_URL.format(channel_id=channel_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
    except Exception as e:
        print(f"  [오류] RSS 피드 가져오기 실패: {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }

    root = ET.fromstring(content)
    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_LOOKBACK)

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if video_id_el is None or title_el is None:
            continue

        published_str = published_el.text if published_el is not None else ""
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            published = datetime.now(timezone.utc)

        if published < cutoff:
            continue

        href = link_el.get("href", "") if link_el is not None else ""
        videos.append(
            {
                "video_id": video_id_el.text,
                "title": title_el.text,
                "url": href or f"https://www.youtube.com/watch?v={video_id_el.text}",
                "published": published_str,
            }
        )

    return videos


def load_processed() -> set[str]:
    if not PROCESSED_FILE.exists():
        return set()
    data = json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))
    return set(data)


def main():
    channels = json.loads(CHANNELS_FILE.read_text(encoding="utf-8"))
    processed = load_processed()

    new_videos = []
    for ch in channels:
        print(f"[{ch['name']}] RSS 피드 확인 중...", file=sys.stderr)
        videos = fetch_rss(ch["channel_id"])
        for v in videos:
            if v["video_id"] not in processed:
                v["channel_name"] = ch["name"]
                new_videos.append(v)
                print(f"  새 영상: {v['title']} ({v['video_id']})", file=sys.stderr)

    if not new_videos:
        print("새 영상 없음", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
