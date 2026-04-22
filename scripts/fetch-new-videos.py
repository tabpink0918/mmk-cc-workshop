#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS.

Falls back to data/seed_videos.json when RSS feeds are unreachable.
"""

import json
import os
import sys
import xml.etree.ElementTree as ET
import urllib.request
from datetime import datetime, timedelta, timezone

CHANNELS_FILE = "data/channels.json"
PROCESSED_FILE = "data/processed.json"
SEED_FILE = "data/seed_videos.json"
MAX_AGE_DAYS = 2  # look back N days for new videos

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def fetch_channel_videos(channel_id, channel_name, max_age_days=MAX_AGE_DAYS):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
    except Exception as e:
        print(f"  [WARN] RSS fetch failed for {channel_name}: {e}", file=sys.stderr)
        return None  # None signals fallback needed

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"  [WARN] RSS parse error for {channel_name}: {e}", file=sys.stderr)
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    videos = []

    for entry in root.findall("atom:entry", NS):
        vid_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)

        if vid_el is None or title_el is None:
            continue

        video_id = vid_el.text.strip()
        title = title_el.text.strip()
        published_str = published_el.text.strip() if published_el is not None else ""

        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            if published < cutoff:
                continue
        except Exception:
            pass

        videos.append(
            {
                "video_id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "published": published_str,
                "channel_name": channel_name,
            }
        )

    return videos


def main():
    channels = load_json(CHANNELS_FILE, [])
    processed = set(load_json(PROCESSED_FILE, []))

    rss_failed_all = False
    new_videos = []

    if channels:
        rss_results = []
        for ch in channels:
            name = ch.get("name", ch.get("channel_id", "?"))
            cid = ch.get("channel_id", "")
            print(f"Checking: {name}", file=sys.stderr)
            result = fetch_channel_videos(cid, name)
            if result is None:
                rss_results.append(False)
            else:
                rss_results.append(True)
                for v in result:
                    if v["video_id"] not in processed:
                        new_videos.append(v)

        rss_failed_all = not any(rss_results)

    if rss_failed_all or not channels:
        print("[INFO] RSS unavailable — using seed_videos.json as fallback", file=sys.stderr)
        seed = load_json(SEED_FILE, [])
        for v in seed:
            if v.get("video_id") not in processed:
                new_videos.append(v)

    # Deduplicate by video_id
    seen = set()
    unique = []
    for v in new_videos:
        if v["video_id"] not in seen:
            seen.add(v["video_id"])
            unique.append(v)
    new_videos = unique

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    print(f"\nNew videos found: {len(new_videos)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
