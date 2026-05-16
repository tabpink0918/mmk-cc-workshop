#!/usr/bin/env python3
"""YouTube RSS 피드에서 새 영상을 확인하는 스크립트."""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

CHANNELS_FILE = "data/channels.json"
PROCESSED_FILE = "data/processed.json"
LOOKBACK_DAYS = 7


def fetch_rss(channel_id: str) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except Exception as e:
        print(f"  RSS 요청 실패: {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(data)
    videos = []
    for entry in root.findall("atom:entry", ns):
        vid_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        pub_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)
        if vid_el is None or title_el is None or pub_el is None:
            continue
        videos.append(
            {
                "video_id": vid_el.text,
                "title": title_el.text,
                "published": pub_el.text,
                "url": link_el.attrib.get("href", f"https://youtu.be/{vid_el.text}")
                if link_el is not None
                else f"https://youtu.be/{vid_el.text}",
            }
        )
    return videos


def main():
    with open(CHANNELS_FILE, encoding="utf-8") as f:
        channels = json.load(f)

    with open(PROCESSED_FILE, encoding="utf-8") as f:
        processed = json.load(f)

    processed_ids = set(processed.get("video_ids", []))
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    new_videos = []
    for ch in channels:
        print(f"[{ch['name']}] RSS 확인 중...", file=sys.stderr)
        videos = fetch_rss(ch["id"])
        for v in videos:
            if v["video_id"] in processed_ids:
                continue
            pub = datetime.fromisoformat(v["published"].replace("Z", "+00:00"))
            if pub < cutoff:
                continue
            new_videos.append({**v, "channel": ch["name"]})
        print(f"  → {len(videos)}개 항목 중 신규 확인", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
