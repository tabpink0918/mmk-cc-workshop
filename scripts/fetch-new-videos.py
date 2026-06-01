#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS feeds."""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.error

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

YOUTUBE_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

# Only show videos published after this date (avoids processing old content)
SINCE_DATE = datetime(2026, 5, 28, tzinfo=timezone.utc)


def load_processed():
    if PROCESSED_FILE.exists():
        data = json.loads(PROCESSED_FILE.read_text())
        return set(data.get("processed_ids", []))
    return set()


def fetch_channel_videos(channel_id):
    url = YOUTUBE_RSS.format(channel_id=channel_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for channel {channel_id}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  Error fetching {channel_id}: {e}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"  Parse error for {channel_id}: {e}", file=sys.stderr)
        return []

    videos = []
    for entry in root.findall("atom:entry", NS):
        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        link_el = entry.find("atom:link", NS)

        if video_id_el is None:
            continue

        video_id = video_id_el.text
        title = title_el.text if title_el is not None else "제목 없음"
        url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        published_str = published_el.text if published_el is not None else ""
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            published = datetime.now(timezone.utc)

        if published >= SINCE_DATE:
            videos.append({"id": video_id, "title": title, "url": url, "published": published_str})

    return videos


def main():
    channels = json.loads(CHANNELS_FILE.read_text())
    processed = load_processed()

    new_videos = []
    for ch in channels:
        name = ch["name"]
        cid = ch["channel_id"]
        print(f"Checking {name} ({cid})...", file=sys.stderr)
        videos = fetch_channel_videos(cid)
        for v in videos:
            if v["id"] not in processed:
                v["channel"] = name
                new_videos.append(v)
                print(f"  NEW: {v['title']}", file=sys.stderr)

    # Output JSON for downstream processing
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
