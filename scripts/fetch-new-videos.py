#!/usr/bin/env python3
"""
한국 증시 YouTube 채널에서 새 영상을 확인합니다.
data/channels.json의 채널 목록을 읽고 RSS 피드로 최근 영상을 가져옵니다.
data/processed.json에 없는 영상만 JSON으로 출력합니다.
"""

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

LOOKBACK_HOURS = 48
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


def fetch_rss(channel_id: str) -> str:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_rss(text: str, channel_name: str) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    videos = []

    for entry in re.findall(r"<entry>(.*?)</entry>", text, re.DOTALL):
        pub_m = re.search(r"<published>(.*?)</published>", entry)
        vid_m = re.search(r"<yt:videoId>(.*?)</yt:videoId>", entry)
        title_m = re.search(r"<title>(.*?)</title>", entry)
        desc_m = re.search(r"<media:description>(.*?)</media:description>", entry, re.DOTALL)

        if not (pub_m and vid_m):
            continue

        try:
            pub_dt = datetime.fromisoformat(pub_m.group(1).strip())
        except ValueError:
            continue

        if pub_dt < cutoff:
            continue

        video_id = vid_m.group(1).strip()
        title = title_m.group(1).strip() if title_m else ""
        description = desc_m.group(1).strip() if desc_m else ""

        videos.append(
            {
                "video_id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "published": pub_m.group(1).strip(),
                "channel": channel_name,
                "description": description,
            }
        )

    return videos


def main():
    channels = json.loads(CHANNELS_FILE.read_text())
    processed = set(json.loads(PROCESSED_FILE.read_text()))

    new_videos = []

    for ch in channels:
        cid = ch["channel_id"]
        name = ch["name"]
        try:
            text = fetch_rss(cid)
            videos = parse_rss(text, name)
            new = [v for v in videos if v["video_id"] not in processed]
            new_videos.extend(new)
            print(
                f"[OK] {name}: {len(videos)}개 최근 영상, {len(new)}개 새 영상",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"[ERR] {name} ({cid}): {e}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
