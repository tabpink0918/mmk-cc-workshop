#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels."""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

# Only return videos published within this many days
LOOKBACK_DAYS = 3


def resolve_handle(handle: str) -> str | None:
    """Resolve a YouTube @handle to a channel ID."""
    url = f"https://www.youtube.com/{handle}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        match = re.search(r'"channelId"\s*:\s*"(UC[A-Za-z0-9_-]{22})"', html)
        if match:
            return match.group(1)
        # fallback: browse endpoint
        match = re.search(r'externalId\\":\\"(UC[A-Za-z0-9_-]{22})', html)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"[WARN] Could not resolve {handle}: {e}", file=sys.stderr)
    return None


def fetch_rss(channel_id: str) -> list[dict]:
    """Return recent video entries from a channel's RSS feed."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except Exception as e:
        print(f"[WARN] RSS fetch failed for {channel_id}: {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        print(f"[WARN] XML parse error for {channel_id}: {e}", file=sys.stderr)
        return []

    videos = []
    for entry in root.findall("atom:entry", ns):
        vid_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        pub_el = entry.find("atom:published", ns)
        if vid_el is None or title_el is None or pub_el is None:
            continue
        videos.append(
            {
                "video_id": vid_el.text,
                "title": title_el.text,
                "published": pub_el.text,
                "url": f"https://www.youtube.com/watch?v={vid_el.text}",
            }
        )
    return videos


def main() -> None:
    channels: list[dict] = json.loads(CHANNELS_FILE.read_text())

    processed_ids: set[str] = set()
    if PROCESSED_FILE.exists():
        data = json.loads(PROCESSED_FILE.read_text())
        processed_ids = set(data.get("processed_ids", []))

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    new_videos: list[dict] = []

    for ch in channels:
        name = ch["name"]
        channel_id: str | None = ch.get("channel_id")
        handle: str | None = ch.get("handle")

        if not channel_id:
            if not handle:
                print(f"[SKIP] {name}: no channel_id or handle", file=sys.stderr)
                continue
            print(f"[INFO] Resolving {handle} ...", file=sys.stderr)
            channel_id = resolve_handle(handle)
            if not channel_id:
                print(f"[SKIP] {name}: could not resolve handle {handle}", file=sys.stderr)
                continue
            print(f"[INFO] {name} -> {channel_id}", file=sys.stderr)

        print(f"[INFO] Fetching RSS for {name} ({channel_id}) ...", file=sys.stderr)
        videos = fetch_rss(channel_id)
        print(f"[INFO] {name}: {len(videos)} videos in feed", file=sys.stderr)

        for v in videos:
            if v["video_id"] in processed_ids:
                continue
            try:
                pub = datetime.fromisoformat(v["published"].replace("Z", "+00:00"))
            except ValueError:
                continue
            if pub < cutoff:
                continue
            v["channel_name"] = name
            new_videos.append(v)

    # sort newest first
    new_videos.sort(key=lambda v: v["published"], reverse=True)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
