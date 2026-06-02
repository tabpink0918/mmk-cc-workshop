#!/usr/bin/env python3
"""
한국 증시 유튜브 채널에서 새 영상을 가져옵니다.
YouTube RSS 피드를 통해 최근 영상을 확인하고 processed.json과 비교합니다.
"""

import json
import sys
import urllib3
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REPO_ROOT = Path(__file__).parent.parent
CHANNELS_FILE = REPO_ROOT / "data" / "channels.json"
PROCESSED_FILE = REPO_ROOT / "data" / "processed.json"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; mmk-workshop-bot/1.0)"}
LOOKBACK_DAYS = 2


def load_processed() -> set:
    if PROCESSED_FILE.exists():
        data = json.loads(PROCESSED_FILE.read_text())
        return set(data.get("processed", []))
    return set()


def fetch_channel_videos(channel_id: str, channel_name: str) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        r = requests.get(url, verify=False, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[{channel_name}] RSS 피드 오류: {e}", file=sys.stderr)
        return []

    root = ET.fromstring(r.text)
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    videos = []

    for entry in root.findall("atom:entry", NS):
        vid_id = entry.find("yt:videoId", NS)
        title = entry.find("atom:title", NS)
        published = entry.find("atom:published", NS)
        author = entry.find("atom:author/atom:name", NS)

        if vid_id is None or title is None or published is None:
            continue

        pub_dt = datetime.fromisoformat(published.text.replace("Z", "+00:00"))
        if pub_dt < cutoff:
            continue

        thumbnail = entry.find("media:group/media:thumbnail", NS)
        thumbnail_url = thumbnail.attrib.get("url", "") if thumbnail is not None else ""

        videos.append({
            "video_id": vid_id.text,
            "title": title.text,
            "url": f"https://www.youtube.com/watch?v={vid_id.text}",
            "published": published.text,
            "channel_name": channel_name,
            "thumbnail": thumbnail_url,
        })

    return videos


def main():
    channels = json.loads(CHANNELS_FILE.read_text())["channels"]
    processed = load_processed()

    new_videos = []
    for ch in channels:
        videos = fetch_channel_videos(ch["channel_id"], ch["name"])
        for v in videos:
            if v["video_id"] not in processed:
                new_videos.append(v)

    if not new_videos:
        print("새 영상 없음")
        return

    print(f"새 영상 {len(new_videos)}개 발견:")
    for v in new_videos:
        print(f"  [{v['channel_name']}] {v['title']}")
        print(f"  URL: {v['url']}")
        print(f"  Published: {v['published']}")

    # JSON 형태로도 출력 (파이프라인 처리용)
    print("\n---JSON---")
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
