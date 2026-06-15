#!/usr/bin/env python3
"""
한국 증시 YouTube 채널에서 최근 24시간 내 새 영상을 가져옵니다.
data/channels.json에서 채널 목록을, data/processed.json에서 처리된 영상 ID를 읽어
아직 처리되지 않은 새 영상 정보를 JSON으로 출력합니다.
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CHANNELS_FILE = REPO_ROOT / "data" / "channels.json"
PROCESSED_FILE = REPO_ROOT / "data" / "processed.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
YOUTUBE_ATOM_NS = "http://www.w3.org/2005/Atom"
YT_NS = "http://www.youtube.com/xml/schemas/2015"
MEDIA_NS = "http://search.yahoo.com/mrss/"

LOOKBACK_HOURS = 24


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_rss(channel_id: str) -> bytes:
    url = RSS_URL.format(channel_id=channel_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def parse_feed(xml_bytes: bytes, channel_name: str) -> list[dict]:
    ns = {
        "atom": YOUTUBE_ATOM_NS,
        "yt": YT_NS,
        "media": MEDIA_NS,
    }
    root = ET.fromstring(xml_bytes)
    entries = []
    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if video_id_el is None or title_el is None or published_el is None:
            continue

        video_id = video_id_el.text.strip()
        title = title_el.text.strip()
        published_str = published_el.text.strip()
        url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        # Parse ISO 8601 date
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        entries.append({
            "video_id": video_id,
            "title": title,
            "url": url,
            "published": published_str,
            "published_dt": published,
            "channel": channel_name,
        })
    return entries


def main():
    channels_data = load_json(CHANNELS_FILE)
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed", []))

    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    new_videos = []
    errors = []

    for ch in channels_data["channels"]:
        channel_id = ch["channel_id"]
        channel_name = ch["name"]
        try:
            xml_bytes = fetch_rss(channel_id)
            entries = parse_feed(xml_bytes, channel_name)
            for entry in entries:
                if entry["video_id"] in processed_ids:
                    continue
                if entry["published_dt"] >= cutoff:
                    new_videos.append({
                        "video_id": entry["video_id"],
                        "title": entry["title"],
                        "url": entry["url"],
                        "published": entry["published"],
                        "channel": entry["channel"],
                    })
        except Exception as e:
            errors.append({"channel": channel_name, "error": str(e)})

    result = {
        "new_videos": new_videos,
        "errors": errors,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "lookback_hours": LOOKBACK_HOURS,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
