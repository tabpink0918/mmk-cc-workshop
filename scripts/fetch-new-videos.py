#!/usr/bin/env python3
"""
한국 증시 유튜브 채널에서 새 영상을 확인하고 출력합니다.
data/channels.json 에서 채널 목록을 읽고, data/processed.json 과 비교해
처리되지 않은 최근 영상 목록을 JSON으로 출력합니다.
"""
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

DAYS_LOOKBACK = 7

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def fetch_rss(channel_id: str) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    r = requests.get(url, verify=False, timeout=15)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    videos = []
    for entry in root.findall("atom:entry", NS):
        vid_id = entry.find("yt:videoId", NS)
        title = entry.find("atom:title", NS)
        published = entry.find("atom:published", NS)
        link = entry.find("atom:link", NS)
        if vid_id is None:
            continue
        videos.append(
            {
                "video_id": vid_id.text,
                "title": title.text if title is not None else "",
                "published": published.text if published is not None else "",
                "url": link.get("href") if link is not None else f"https://www.youtube.com/watch?v={vid_id.text}",
            }
        )
    return videos


def main():
    channels = load_json(CHANNELS_FILE, [])
    processed = set(load_json(PROCESSED_FILE, []))
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_LOOKBACK)

    new_videos = []
    for ch in channels:
        name = ch.get("name", "")
        cid = ch.get("channel_id", "")
        print(f"  채널 확인 중: {name} ({cid})", file=sys.stderr)
        try:
            videos = fetch_rss(cid)
        except Exception as e:
            print(f"  [오류] {name}: {e}", file=sys.stderr)
            continue

        for v in videos:
            if v["video_id"] in processed:
                continue
            try:
                pub_dt = datetime.fromisoformat(v["published"].replace("Z", "+00:00"))
            except ValueError:
                continue
            if pub_dt >= cutoff:
                new_videos.append(
                    {
                        "channel": name,
                        "video_id": v["video_id"],
                        "title": v["title"],
                        "published": v["published"],
                        "url": v["url"],
                    }
                )

    new_videos.sort(key=lambda x: x["published"], reverse=True)
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    print(f"\n총 {len(new_videos)}개의 새 영상을 찾았습니다.", file=sys.stderr)


if __name__ == "__main__":
    main()
