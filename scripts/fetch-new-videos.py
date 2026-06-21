#!/usr/bin/env python3
"""YouTube RSS를 이용해 채널별 새 영상을 확인하고 new_videos.json에 저장합니다."""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"
OUTPUT_FILE = BASE_DIR / "data" / "new_videos.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

# 몇 일 이내의 영상만 체크 (최근 2일)
DAYS_THRESHOLD = 2


def fetch_rss(channel_id: str) -> list[dict]:
    url = RSS_URL.format(channel_id=channel_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        root = ET.fromstring(data)
    except Exception as e:
        print(f"  [!] RSS 조회 실패 ({channel_id}): {e}", file=sys.stderr)
        return []

    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_THRESHOLD)
    for entry in root.findall("atom:entry", NS):
        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        if video_id_el is None or title_el is None or published_el is None:
            continue
        published_str = published_el.text.strip()
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if published < cutoff:
            continue
        videos.append({
            "video_id": video_id_el.text.strip(),
            "title": title_el.text.strip(),
            "url": f"https://www.youtube.com/watch?v={video_id_el.text.strip()}",
            "published": published_str,
        })
    return videos


def main():
    channels = json.loads(CHANNELS_FILE.read_text())["channels"]
    processed = set(json.loads(PROCESSED_FILE.read_text()).get("processed_video_ids", []))

    new_videos = []
    for ch in channels:
        print(f"채널 확인 중: {ch['name']} ({ch['channel_id']})")
        videos = fetch_rss(ch["channel_id"])
        for v in videos:
            if v["video_id"] not in processed:
                v["channel_name"] = ch["name"]
                new_videos.append(v)
                print(f"  새 영상: [{v['published']}] {v['title']}")

    OUTPUT_FILE.write_text(json.dumps({"new_videos": new_videos}, ensure_ascii=False, indent=2))
    print(f"\n총 {len(new_videos)}개의 새 영상을 발견했습니다.")
    print(f"결과 저장: {OUTPUT_FILE}")
    return len(new_videos)


if __name__ == "__main__":
    count = main()
    sys.exit(0)
