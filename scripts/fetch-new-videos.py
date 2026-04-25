#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS feed."""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

LOOKBACK_HOURS = 48


def fetch_rss(channel_id: str) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
    except Exception as e:
        print(f"  [RSS error] {channel_id}: {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"  [XML parse error] {channel_id}: {e}", file=sys.stderr)
        return []

    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if video_id_el is None or title_el is None:
            continue

        video_id = video_id_el.text
        title = title_el.text or ""
        published_str = published_el.text if published_el is not None else ""
        video_url = link_el.get("href", f"https://www.youtube.com/watch?v={video_id}") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        # Parse published date
        published = None
        if published_str:
            try:
                published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        if published and published < cutoff:
            continue

        videos.append({
            "video_id": video_id,
            "title": title,
            "url": video_url,
            "published": published_str,
        })

    return videos


def main():
    channels_data = json.loads(CHANNELS_FILE.read_text())
    processed_data = json.loads(PROCESSED_FILE.read_text())
    processed_ids = set(processed_data.get("processed_video_ids", []))

    new_videos = []

    for channel in channels_data["channels"]:
        print(f"Checking {channel['name']} ({channel['channel_id']})...")
        videos = fetch_rss(channel["channel_id"])
        for v in videos:
            if v["video_id"] not in processed_ids:
                v["channel_name"] = channel["name"]
                new_videos.append(v)
                print(f"  NEW: [{v['published'][:10] if v['published'] else 'unknown'}] {v['title']}")

    if not new_videos:
        print("No new videos found.")
    else:
        print(f"\nFound {len(new_videos)} new video(s).")

    print(json.dumps(new_videos, ensure_ascii=False))


if __name__ == "__main__":
    main()
