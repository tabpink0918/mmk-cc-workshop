#!/usr/bin/env python3
"""
Fetch new videos from Korean stock market YouTube channels via RSS feeds.
Outputs new (unprocessed) videos as JSON to stdout.
"""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.error

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_URL_CHANNEL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
RSS_URL_USER = "https://www.youtube.com/feeds/videos.xml?user={user}"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

LOOKBACK_HOURS = 48


def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def fetch_rss(channel_id=None, user=None):
    if user:
        url = RSS_URL_USER.format(user=user)
    else:
        url = RSS_URL_CHANNEL.format(channel_id=channel_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        print(f"[WARN] Failed to fetch RSS for {channel_id}: {e}", file=sys.stderr)
        return None


def parse_videos(xml_bytes, channel_name):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[WARN] XML parse error: {e}", file=sys.stderr)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    videos = []

    for entry in root.findall("atom:entry", NS):
        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        link_el = entry.find("atom:link", NS)

        if video_id_el is None or title_el is None or published_el is None:
            continue

        video_id = video_id_el.text
        title = title_el.text or ""
        published_str = published_el.text or ""
        url = f"https://www.youtube.com/watch?v={video_id}"
        if link_el is not None:
            url = link_el.get("href", url)

        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if published >= cutoff:
            videos.append({
                "video_id": video_id,
                "title": title,
                "channel": channel_name,
                "published": published_str,
                "url": url,
            })

    return videos


def main():
    channels_data = load_json(CHANNELS_FILE)
    processed_data = load_json(PROCESSED_FILE)

    processed_ids = set(processed_data.get("processed", []))
    channels = channels_data.get("channels", [])

    new_videos = []

    for ch in channels:
        channel_id = ch.get("channel_id", "")
        user = ch.get("user", "")
        channel_name = ch.get("name", channel_id or user)
        print(f"[INFO] Checking channel: {channel_name}", file=sys.stderr)

        xml_bytes = fetch_rss(channel_id=channel_id if channel_id else None,
                              user=user if user else None)
        if xml_bytes is None:
            continue

        videos = parse_videos(xml_bytes, channel_name)
        for v in videos:
            if v["video_id"] not in processed_ids:
                new_videos.append(v)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
