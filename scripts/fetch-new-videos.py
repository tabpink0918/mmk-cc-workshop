#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS."""

import json
import requests
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHANNELS_FILE = ROOT / "data" / "channels.json"
PROCESSED_FILE = ROOT / "data" / "processed.json"
OUTPUT_FILE = Path("/tmp/new_videos.json")

LOOKBACK_DAYS = 7


def load_processed():
    if PROCESSED_FILE.exists():
        data = json.loads(PROCESSED_FILE.read_text())
        return set(data) if isinstance(data, list) else set(data.get("video_ids", []))
    return set()


RSS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Feedfetcher-Google; +http://www.google.com/feedfetcher.html)",
    "Accept": "application/atom+xml,application/xml,text/xml,*/*",
}


def fetch_channel_videos(channel_id, channel_name):
    import time
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    last_err = None
    for attempt in range(4):
        if attempt:
            time.sleep(2 ** attempt)
        try:
            r = requests.get(url, headers=RSS_HEADERS, timeout=10)
            r.raise_for_status()
            break
        except Exception as e:
            last_err = e
    else:
        raise last_err

    videos = []
    for entry in re.findall(r"<entry>(.*?)</entry>", r.text, re.DOTALL):
        vid_id = re.search(r"<yt:videoId>(.+?)</yt:videoId>", entry)
        title = re.search(r"<title>(.+?)</title>", entry)
        published = re.search(r"<published>(.+?)</published>", entry)
        if vid_id and title and published:
            videos.append({
                "video_id": vid_id.group(1),
                "title": title.group(1),
                "published": published.group(1),
                "channel": channel_name,
                "url": f"https://www.youtube.com/watch?v={vid_id.group(1)}",
            })
    return videos


def main():
    if not CHANNELS_FILE.exists():
        print(f"오류: {CHANNELS_FILE} 없음", file=sys.stderr)
        sys.exit(1)

    channels = json.loads(CHANNELS_FILE.read_text())
    processed = load_processed()
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    new_videos = []
    for ch in channels:
        try:
            videos = fetch_channel_videos(ch["channel_id"], ch["name"])
            fresh = []
            for v in videos:
                if v["video_id"] in processed:
                    continue
                try:
                    pub_dt = datetime.fromisoformat(v["published"].replace("Z", "+00:00"))
                    if pub_dt < cutoff:
                        continue
                except Exception:
                    pass
                fresh.append(v)
            new_videos.extend(fresh)
            print(f"✓ {ch['name']}: 최근 {len(videos)}개 중 신규 {len(fresh)}개")
        except Exception as e:
            print(f"✗ {ch['name']}: {e}", file=sys.stderr)

    if not new_videos:
        print("\n새 영상 없음 — 모두 처리 완료")
    else:
        print(f"\n새 영상 {len(new_videos)}개 발견:")
        for v in new_videos:
            print(f"  [{v['channel']}] {v['published'][:10]} | {v['title'][:70]}")
            print(f"    {v['url']}")

    OUTPUT_FILE.write_text(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return len(new_videos)


if __name__ == "__main__":
    count = main()
    sys.exit(0 if count >= 0 else 1)
