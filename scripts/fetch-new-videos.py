#!/usr/bin/env python3
"""Fetch new YouTube videos from Korean stock market channels."""

import json
import sys
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"
DAYS_LOOKBACK = 7

NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def resolve_channel_id(handle: str) -> str | None:
    """Resolve YouTube @handle to channel_id by fetching the channel page."""
    url = f"https://www.youtube.com/{handle}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        match = re.search(r'"channelId":"(UC[A-Za-z0-9_-]{22})"', html)
        if match:
            return match.group(1)
        match = re.search(r'channel_id=([A-Za-z0-9_-]+)', html)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"  [warn] handle resolution failed for {handle}: {e}", file=sys.stderr)
    return None


def fetch_rss(channel_id: str) -> list[dict]:
    """Fetch RSS feed for a channel and return list of video dicts."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
    except Exception as e:
        print(f"  [warn] RSS fetch failed for {channel_id}: {e}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"  [warn] XML parse failed for {channel_id}: {e}", file=sys.stderr)
        return []

    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_LOOKBACK)

    for entry in root.findall("atom:entry", NS):
        vid_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        link_el = entry.find("atom:link", NS)

        if vid_id_el is None or title_el is None or published_el is None:
            continue

        video_id = vid_id_el.text
        title = title_el.text or ""
        published_str = published_el.text or ""
        url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if published >= cutoff:
            videos.append({
                "video_id": video_id,
                "title": title,
                "url": url,
                "published": published_str,
            })

    return videos


def main():
    channels = json.loads(CHANNELS_FILE.read_text())
    processed = set(json.loads(PROCESSED_FILE.read_text()))

    new_videos = []

    for ch in channels:
        name = ch["name"]
        channel_id = ch.get("channel_id")
        handle = ch.get("handle")

        if not channel_id and handle:
            print(f"Resolving {handle} ...", file=sys.stderr)
            channel_id = resolve_channel_id(handle)
            if channel_id:
                ch["channel_id"] = channel_id
            else:
                print(f"  [skip] could not resolve {name}", file=sys.stderr)
                continue

        print(f"Checking {name} ({channel_id}) ...", file=sys.stderr)
        videos = fetch_rss(channel_id)
        fresh = [v for v in videos if v["video_id"] not in processed]
        print(f"  {len(fresh)} new / {len(videos)} recent", file=sys.stderr)
        for v in fresh:
            v["channel_name"] = name
            new_videos.append(v)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
