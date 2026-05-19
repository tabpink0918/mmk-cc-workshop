#!/usr/bin/env python3
"""한국 증시 유튜브 채널에서 새 영상을 가져오는 스크립트."""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

CHANNELS = [
    {"name": "슈카월드",   "channel_id": "UCsJ6RuBiTVWRX156FVbeaGg"},
    {"name": "삼프로TV",   "channel_id": "UChlv4GSd7OQl3js-jkLOnFA"},
    {"name": "월가아재의 과학적 투자", "channel_id": "UCpqD9_OJNtF6suPpi6mOQCQ"},
]

RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
DAYS_BACK = 2  # 최근 N일 이내 영상만 체크


def load_processed():
    path = Path(__file__).parent.parent / "data" / "processed.json"
    if path.exists():
        return set(json.loads(path.read_text()))
    return set()


def fetch_channel_videos(channel_id: str) -> list[dict]:
    url = RSS_BASE.format(channel_id)
    try:
        with urlopen(url, timeout=10) as resp:
            content = resp.read()
    except URLError as e:
        print(f"  [WARN] RSS 가져오기 실패 ({url}): {e}", file=sys.stderr)
        return []

    root = ET.fromstring(content)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt":   "http://www.youtube.com/xml/schemas/2015",
        "media":"http://search.yahoo.com/mrss/",
    }

    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    videos = []

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el    = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)

        if video_id_el is None or title_el is None or published_el is None:
            continue

        published = datetime.fromisoformat(published_el.text.replace("Z", "+00:00"))
        if published < cutoff:
            continue

        videos.append({
            "video_id":  video_id_el.text,
            "title":     title_el.text,
            "url":       f"https://www.youtube.com/watch?v={video_id_el.text}",
            "published": published_el.text,
        })

    return videos


def main():
    processed = load_processed()
    new_videos = []

    for ch in CHANNELS:
        print(f"채널 확인 중: {ch['name']} ...", file=sys.stderr)
        videos = fetch_channel_videos(ch["channel_id"])
        for v in videos:
            if v["video_id"] not in processed:
                v["channel"] = ch["name"]
                new_videos.append(v)

    # 최신순 정렬
    new_videos.sort(key=lambda x: x["published"], reverse=True)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    print(f"\n총 {len(new_videos)}개의 새 영상 발견", file=sys.stderr)


if __name__ == "__main__":
    main()
