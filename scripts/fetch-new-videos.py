#!/usr/bin/env python3
"""
한국 증시 YouTube 채널에서 신규 영상을 확인하는 스크립트.
data/channels.json에 정의된 채널에서 RSS 피드를 읽어
data/processed.json에 없는 새 영상만 출력합니다.
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

HOURS_LOOKBACK = 24  # 최근 24시간 내 영상만 확인


def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def fetch_rss(channel_id: str) -> list[dict]:
    url = RSS_URL.format(channel_id=channel_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()
    except Exception as e:
        print(f"  [경고] RSS 가져오기 실패 ({channel_id}): {e}", file=sys.stderr)
        return []

    root = ET.fromstring(xml_data)
    videos = []
    cutoff = datetime.now(timezone.utc).timestamp() - HOURS_LOOKBACK * 3600

    for entry in root.findall("atom:entry", NS):
        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        link_el = entry.find("atom:link", NS)

        if video_id_el is None:
            continue

        video_id = video_id_el.text
        title = title_el.text if title_el is not None else "(제목 없음)"
        published_str = published_el.text if published_el is not None else ""
        url = link_el.attrib.get("href", f"https://www.youtube.com/watch?v={video_id}") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        # 24시간 이내 영상만 포함
        try:
            published_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            if published_dt.timestamp() < cutoff:
                continue
        except (ValueError, AttributeError):
            pass

        videos.append({
            "video_id": video_id,
            "title": title,
            "published": published_str,
            "url": url,
        })

    return videos


def main():
    channels_data = load_json(CHANNELS_FILE)
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed_video_ids", []))

    new_videos = []

    for channel in channels_data.get("channels", []):
        name = channel.get("name", channel["channel_id"])
        channel_id = channel["channel_id"]
        print(f"[{name}] RSS 확인 중...", file=sys.stderr)

        videos = fetch_rss(channel_id)
        for v in videos:
            if v["video_id"] not in processed_ids:
                v["channel_name"] = name
                new_videos.append(v)
                print(f"  → 새 영상: {v['title']} ({v['video_id']})", file=sys.stderr)

    if not new_videos:
        print("새 영상 없음.", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
