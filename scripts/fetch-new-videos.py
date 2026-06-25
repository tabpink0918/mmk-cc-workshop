#!/usr/bin/env python3
"""
한국 증시 유튜브 채널에서 새 영상을 확인하는 스크립트.
channels.json에 정의된 채널의 RSS 피드를 체크하고
processed.json에 없는 새 영상을 출력합니다.
"""
import json
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

LOOKBACK_HOURS = 48


def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def fetch_rss(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for channel {channel_id}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error fetching {channel_id}: {e}", file=sys.stderr)
        return None


def parse_videos(xml_bytes, channel_name):
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"  XML parse error: {e}", file=sys.stderr)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    videos = []

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if video_id_el is None or title_el is None:
            continue

        video_id = video_id_el.text
        title = title_el.text or ""
        url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        published_str = published_el.text if published_el is not None else ""
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            published = datetime.now(timezone.utc)

        if published >= cutoff:
            videos.append({
                "video_id": video_id,
                "title": title,
                "url": url,
                "published": published_str,
                "channel": channel_name,
            })

    return videos


def main():
    channels = load_json(CHANNELS_FILE)
    processed = set(load_json(PROCESSED_FILE))

    if not channels:
        print("channels.json이 비어 있습니다.", file=sys.stderr)
        sys.exit(1)

    new_videos = []
    for ch in channels:
        name = ch.get("name", ch.get("channel_id"))
        channel_id = ch.get("channel_id")
        print(f"채널 확인 중: {name} ({channel_id})", file=sys.stderr)

        xml_bytes = fetch_rss(channel_id)
        if xml_bytes is None:
            continue

        videos = parse_videos(xml_bytes, name)
        fresh = [v for v in videos if v["video_id"] not in processed]
        print(f"  최근 {LOOKBACK_HOURS}h 영상 {len(videos)}개, 신규 {len(fresh)}개", file=sys.stderr)
        new_videos.extend(fresh)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
