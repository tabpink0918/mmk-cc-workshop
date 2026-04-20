#!/usr/bin/env python3
"""
한국 증시 유튜브 채널에서 새 영상을 확인하는 스크립트.
data/channels.json 에서 채널 목록을 읽고,
data/processed.json 에 없는 최근 영상을 출력합니다.
"""

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"
DAYS_LOOKBACK = 90

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_rss(channel_id, retries=3):
    import time
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def parse_rss(xml, channel_name):
    entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
    videos = []
    for entry in entries:
        vid_match = re.search(r"<yt:videoId>([^<]+)</yt:videoId>", entry)
        pub_match = re.search(r"<published>([^<]+)</published>", entry)
        title_match = re.search(r"<title>([^<]+)</title>", entry)
        if not (vid_match and pub_match and title_match):
            continue
        video_id = vid_match.group(1).strip()
        published_str = pub_match.group(1).strip()
        title = title_match.group(1).strip()
        # HTML entity decode
        title = title.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        videos.append({
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": title,
            "published": published_str,
            "channel": channel_name,
        })
    return videos


def main():
    channels = load_json(CHANNELS_FILE)
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed", []))

    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_LOOKBACK)
    new_videos = []

    for ch in channels:
        name = ch["name"]
        ch_id = ch["channel_id"]
        print(f"[채널 확인] {name} ...", file=sys.stderr)
        try:
            xml = fetch_rss(ch_id)
            videos = parse_rss(xml, name)
            for v in videos:
                if v["video_id"] in processed_ids:
                    continue
                pub = datetime.fromisoformat(v["published"].replace("Z", "+00:00"))
                if pub < cutoff:
                    continue
                new_videos.append(v)
            print(f"  → {len(videos)}개 중 새 영상: {sum(1 for v in videos if v['video_id'] not in processed_ids and datetime.fromisoformat(v['published'].replace('Z', '+00:00')) >= cutoff)}개", file=sys.stderr)
        except Exception as e:
            print(f"  → ERROR: {e}", file=sys.stderr)

    # Sort by published date descending
    new_videos.sort(key=lambda v: v["published"], reverse=True)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    print(f"\n총 {len(new_videos)}개 새 영상 발견", file=sys.stderr)


if __name__ == "__main__":
    main()
