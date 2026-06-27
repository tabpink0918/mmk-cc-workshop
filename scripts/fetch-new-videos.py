#!/usr/bin/env python3
"""
한국 증시 유튜브 채널 새 영상 확인 스크립트
YouTube RSS 피드를 통해 각 채널의 최신 영상을 확인하고,
processed.json에 없는 새 영상만 출력합니다.
"""

import json
import requests
import xml.etree.ElementTree as ET
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

# 최근 N시간 이내 영상만 신규로 간주
RECENT_HOURS = 48


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def fetch_rss(channel_id: str) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        print(f"  RSS 오류 ({channel_id}): {e}", file=sys.stderr)
        return []

    root = ET.fromstring(resp.content)
    entries = []
    for entry in root.findall("atom:entry", RSS_NS):
        video_id = entry.find("yt:videoId", RSS_NS).text
        title = entry.find("atom:title", RSS_NS).text
        published_str = entry.find("atom:published", RSS_NS).text
        link_el = entry.find("atom:link", RSS_NS)
        video_url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        entries.append(
            {
                "video_id": video_id,
                "title": title,
                "published": published,
                "url": video_url,
            }
        )
    return entries


def main():
    channels = load_json(CHANNELS_FILE)["channels"]
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed_video_ids", []))

    cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_HOURS)
    new_videos = []

    for ch in channels:
        name = ch["name"]
        channel_id = ch["channel_id"]
        print(f"[{name}] 확인 중...", file=sys.stderr)
        videos = fetch_rss(channel_id)

        for v in videos:
            if v["video_id"] in processed_ids:
                continue
            if v["published"] < cutoff:
                continue
            new_videos.append(
                {
                    "channel": name,
                    "video_id": v["video_id"],
                    "title": v["title"],
                    "published": v["published"].isoformat(),
                    "url": v["url"],
                }
            )

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
