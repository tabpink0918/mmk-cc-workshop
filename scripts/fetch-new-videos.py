#!/usr/bin/env python3
"""YouTube 채널 RSS 피드에서 신규 영상을 확인하여 JSON으로 출력."""

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
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}
MAX_AGE_HOURS = 48


def load_processed():
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text()))
    return set()


def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def parse_feed(xml_bytes, channel_name, cutoff):
    root = ET.fromstring(xml_bytes)
    videos = []
    for entry in root.findall("atom:entry", NS):
        video_id = entry.findtext("yt:videoId", namespaces=NS)
        title = entry.findtext("atom:title", namespaces=NS, default="")
        published_str = entry.findtext("atom:published", namespaces=NS, default="")
        link_el = entry.find("atom:link[@rel='alternate']", NS)
        url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if published >= cutoff:
            videos.append({
                "video_id": video_id,
                "url": url,
                "title": title,
                "channel": channel_name,
                "published": published_str[:10],
            })
    return videos


def main():
    channels = json.loads(CHANNELS_FILE.read_text())
    processed = load_processed()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    new_videos = []

    for ch in channels:
        name = ch["name"]
        cid = ch["channel_id"]
        try:
            xml_bytes = fetch_rss(cid)
            videos = parse_feed(xml_bytes, name, cutoff)
            for v in videos:
                if v["video_id"] not in processed:
                    new_videos.append(v)
                    print(f"[NEW] {v['published']} | {name} | {v['video_id']} | {v['title']}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] {name} RSS 실패: {e}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
