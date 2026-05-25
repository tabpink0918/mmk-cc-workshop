#!/usr/bin/env python3
"""
한국 증시 YouTube 채널에서 최근 24시간 내 새 영상을 확인합니다.
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
HOURS_WINDOW = 48  # 최근 48시간 이내 영상 확인


def load_channels():
    with open(CHANNELS_FILE) as f:
        return json.load(f)["channels"]


def load_processed():
    if not PROCESSED_FILE.exists():
        return []
    with open(PROCESSED_FILE) as f:
        return json.load(f).get("processed", [])


def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read()
    except Exception as e:
        print(f"  [오류] RSS 가져오기 실패: {e}", file=sys.stderr)
        return None


def parse_videos(xml_data, channel_name):
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(xml_data)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_WINDOW)
    videos = []

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if video_id_el is None or title_el is None or published_el is None:
            continue

        published_str = published_el.text.strip()
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if published < cutoff:
            continue

        video_id = video_id_el.text.strip()
        url = f"https://www.youtube.com/watch?v={video_id}"
        if link_el is not None:
            url = link_el.get("href", url)

        videos.append({
            "video_id": video_id,
            "title": title_el.text.strip(),
            "url": url,
            "published": published_str,
            "channel": channel_name,
        })

    return videos


def main():
    channels = load_channels()
    processed = set(load_processed())
    new_videos = []

    for ch in channels:
        print(f"채널 확인 중: {ch['name']}", file=sys.stderr)
        xml_data = fetch_rss(ch["channel_id"])
        if xml_data is None:
            continue
        videos = parse_videos(xml_data, ch["name"])
        for v in videos:
            if v["video_id"] not in processed:
                new_videos.append(v)
                print(f"  새 영상 발견: {v['title']}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
