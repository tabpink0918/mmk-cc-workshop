#!/usr/bin/env python3
"""
한국 증시 유튜브 채널의 새 영상을 확인하고 JSON으로 출력합니다.
channels.json에 정의된 채널들의 RSS 피드를 파싱하여 processed.json에 없는 새 영상을 반환합니다.
"""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"
PROCESSED_FILE = DATA_DIR / "processed.json"
DAYS_LOOKBACK = 7

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def load_channels():
    with open(CHANNELS_FILE, encoding="utf-8") as f:
        return json.load(f)["channels"]


def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE, encoding="utf-8") as f:
            return set(json.load(f).get("processed", []))
    return set()


def fetch_rss(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as e:
        print(f"  [경고] RSS 가져오기 실패 ({channel_id}): {e}", file=sys.stderr)
        return None


def parse_videos(rss_content, channel_name):
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_LOOKBACK)
    try:
        root = ET.fromstring(rss_content)
    except ET.ParseError as e:
        print(f"  [경고] RSS 파싱 실패: {e}", file=sys.stderr)
        return []

    videos = []
    for entry in root.findall("atom:entry", NS):
        vid_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)

        if vid_el is None or title_el is None or published_el is None:
            continue

        pub_str = published_el.text.replace("Z", "+00:00")
        try:
            pub_date = datetime.fromisoformat(pub_str)
        except ValueError:
            continue

        if pub_date < cutoff:
            continue

        videos.append({
            "video_id": vid_el.text,
            "title": title_el.text,
            "url": f"https://www.youtube.com/watch?v={vid_el.text}",
            "channel": channel_name,
            "published": published_el.text,
        })

    return videos


def main():
    channels = load_channels()
    processed = load_processed()

    new_videos = []
    for ch in channels:
        print(f"채널 확인 중: {ch['name']} ...", file=sys.stderr)
        rss = fetch_rss(ch["channel_id"])
        if not rss:
            continue
        videos = parse_videos(rss, ch["name"])
        for v in videos:
            if v["video_id"] not in processed:
                new_videos.append(v)
                print(f"  새 영상: {v['title']}", file=sys.stderr)

    if not new_videos:
        print("새 영상 없음.", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
