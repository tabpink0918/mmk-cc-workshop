#!/usr/bin/env python3
"""한국 증시 YouTube 채널에서 신규 영상을 가져오는 스크립트."""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.error

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
# 최근 48시간 이내 영상만 새 영상으로 판단
NEW_VIDEO_HOURS = 48


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_rss(channel_id: str) -> list[dict]:
    url = YOUTUBE_RSS_URL.format(channel_id=channel_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
    except urllib.error.HTTPError as e:
        print(f"  [WARN] HTTP {e.code} for channel {channel_id}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [WARN] Failed to fetch RSS for {channel_id}: {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"  [WARN] XML parse error for {channel_id}: {e}", file=sys.stderr)
        return []

    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=NEW_VIDEO_HOURS)

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if video_id_el is None or title_el is None:
            continue

        video_id = video_id_el.text
        title = title_el.text or ""
        link = link_el.get("href", f"https://www.youtube.com/watch?v={video_id}") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        published_str = published_el.text if published_el is not None else None
        published_dt = None
        if published_str:
            try:
                published_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        if published_dt and published_dt < cutoff:
            continue

        videos.append({
            "video_id": video_id,
            "title": title,
            "url": link,
            "published": published_str or "",
        })

    return videos


def main():
    channels_data = load_json(CHANNELS_FILE)
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed_ids", []))

    new_videos = []
    for channel in channels_data["channels"]:
        name = channel["name"]
        channel_id = channel["channel_id"]
        print(f"채널 확인 중: {name} ({channel_id})", file=sys.stderr)

        videos = fetch_rss(channel_id)
        for v in videos:
            if v["video_id"] not in processed_ids:
                v["channel"] = name
                new_videos.append(v)
                print(f"  새 영상: {v['title']}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
