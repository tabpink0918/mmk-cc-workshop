#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS feeds."""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.error

DATA_DIR = Path(__file__).parent.parent / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"
PROCESSED_FILE = DATA_DIR / "processed.json"

# Only show videos from the last 3 days
LOOKBACK_DAYS = 3


def fetch_rss(channel_id: str) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
    except urllib.error.URLError as e:
        print(f"  [warn] RSS fetch failed for {channel_id}: {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"  [warn] XML parse error for {channel_id}: {e}", file=sys.stderr)
        return []

    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if video_id_el is None or title_el is None:
            continue

        published_str = published_el.text if published_el is not None else ""
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            published = datetime.now(timezone.utc)

        if published < cutoff:
            continue

        url = link_el.get("href", f"https://www.youtube.com/watch?v={video_id_el.text}") if link_el is not None else f"https://www.youtube.com/watch?v={video_id_el.text}"

        videos.append({
            "video_id": video_id_el.text,
            "title": title_el.text or "",
            "url": url,
            "published": published_str,
        })

    return videos


def main():
    channels = json.loads(CHANNELS_FILE.read_text())
    processed = set(json.loads(PROCESSED_FILE.read_text()))

    new_videos = []
    for ch in channels:
        print(f"Checking: {ch['name']} ...", file=sys.stderr)
        videos = fetch_rss(ch["channel_id"])
        for v in videos:
            if v["video_id"] not in processed:
                v["channel_name"] = ch["name"]
                new_videos.append(v)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0 if new_videos else 1


if __name__ == "__main__":
    sys.exit(main())
