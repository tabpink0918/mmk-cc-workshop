#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS feeds."""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
PROCESSED_FILE = os.path.join(DATA_DIR, "processed.json")

RSS_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "48"))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_channel_id(handle_url: str, session: requests.Session) -> str | None:
    """Resolve a YouTube channel handle URL to its channel_id."""
    try:
        resp = session.get(handle_url, timeout=15)
        resp.raise_for_status()
        for pattern in [
            r'"channelId":"(UC[^"]{22})"',
            r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[^"]{22})"',
            r'"externalId":"(UC[^"]{22})"',
        ]:
            m = re.search(pattern, resp.text)
            if m:
                return m.group(1)
    except Exception as e:
        print(f"  [WARN] Failed to resolve {handle_url}: {e}", file=sys.stderr)
    return None


def fetch_rss(channel_id: str, session: requests.Session) -> list[dict]:
    """Return list of video dicts from YouTube RSS feed."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        videos = []
        for entry in root.findall("atom:entry", RSS_NS):
            vid_id = entry.findtext("yt:videoId", namespaces=RSS_NS)
            title = entry.findtext("atom:title", namespaces=RSS_NS)
            published = entry.findtext("atom:published", namespaces=RSS_NS)
            link_el = entry.find("atom:link", RSS_NS)
            link = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={vid_id}"
            if vid_id:
                videos.append({
                    "video_id": vid_id,
                    "title": title or "",
                    "published": published or "",
                    "url": link,
                })
        return videos
    except Exception as e:
        print(f"  [WARN] Failed to fetch RSS for {channel_id}: {e}", file=sys.stderr)
        return []


def is_recent(published_str: str, hours: int) -> bool:
    """Check if a video was published within the last `hours` hours."""
    if not published_str:
        return False
    try:
        dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return dt >= cutoff
    except Exception:
        return False


def main():
    channels = load_json(CHANNELS_FILE).get("channels", [])
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed_videos", []))

    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (compatible; mmk-cc-workshop/1.0)"
    )

    new_videos = []

    for ch in channels:
        name = ch.get("name", "")
        handle = ch.get("handle", "")
        channel_id = ch.get("channel_id")

        print(f"Checking {name} ({handle})...", file=sys.stderr)

        if not channel_id:
            channel_id = get_channel_id(handle, session)
            if not channel_id:
                print(f"  [SKIP] Could not resolve channel_id for {name}", file=sys.stderr)
                continue
            print(f"  Resolved channel_id: {channel_id}", file=sys.stderr)

        videos = fetch_rss(channel_id, session)
        for v in videos:
            if v["video_id"] in processed_ids:
                continue
            if not is_recent(v["published"], LOOKBACK_HOURS):
                continue
            v["channel_name"] = name
            new_videos.append(v)
            print(f"  NEW: {v['title']} ({v['published']})", file=sys.stderr)

    # Output as JSON to stdout for the caller to consume
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
