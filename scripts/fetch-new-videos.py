#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS."""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

CHANNELS = [
    {"name": "삼프로TV", "channel_id": "UChlv4GSd7OQl3js-jkLOnFA"},
    {"name": "슈카월드", "channel_id": "UCsJ6RuBiTVWRX156FVbeaGg"},
    {"name": "언더스탠딩", "channel_id": "UCIUni4ScRp4mqPXsxy62L5w"},
    {"name": "한국경제TV", "channel_id": "UCF8AeLlUbEpKju6v1H6p8Eg"},
    {"name": "한국경제TV 주식창", "channel_id": "UCT2ZyrFL2JyLIdwwTUG_zpg"},
]

PROCESSED_FILE = Path(__file__).parent.parent / "data" / "processed.json"
LOOKBACK_HOURS = 48


def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    return set()


def fetch_channel_videos(channel_id, channel_name):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read()

    root = ET.fromstring(content)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }

    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    videos = []

    for entry in root.findall("atom:entry", ns):
        vid_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        pub_el = entry.find("atom:published", ns)
        if vid_el is None or title_el is None or pub_el is None:
            continue

        video_id = vid_el.text
        title = title_el.text
        published = pub_el.text
        pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))

        if pub_dt >= cutoff:
            videos.append({
                "video_id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "published": published,
                "channel": channel_name,
            })

    return videos


def main():
    processed = load_processed()
    new_videos = []

    for ch in CHANNELS:
        try:
            videos = fetch_channel_videos(ch["channel_id"], ch["name"])
            for v in videos:
                if v["video_id"] not in processed:
                    new_videos.append(v)
            print(f"[OK] {ch['name']}: {len(videos)} recent, "
                  f"{sum(1 for v in videos if v['video_id'] not in processed)} new",
                  file=sys.stderr)
        except Exception as e:
            print(f"[ERR] {ch['name']}: {e}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
