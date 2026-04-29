#!/usr/bin/env python3
"""
Fetch new videos from Korean stock market YouTube channels via RSS feeds.
Outputs JSON list of new (unprocessed) videos to stdout.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
CHANNELS_FILE = ROOT / "data" / "channels.json"
PROCESSED_FILE = ROOT / "data" / "processed.json"

RSS_BY_HANDLE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
CHANNEL_PAGE = "https://www.youtube.com/@{handle}/videos"


def resolve_channel_id(handle: str) -> str | None:
    """Fetch channel page and extract channel ID from HTML."""
    url = CHANNEL_PAGE.format(handle=handle)
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        match = re.search(r'"channelId":"(UC[A-Za-z0-9_-]{22})"', resp.text)
        if match:
            return match.group(1)
        # fallback: externalId
        match = re.search(r'"externalId":"(UC[A-Za-z0-9_-]{22})"', resp.text)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"  [warn] 채널 페이지 조회 실패 ({handle}): {e}", file=sys.stderr)
    return None


def fetch_rss(channel_id: str) -> list[dict]:
    """Return list of video dicts from YouTube RSS feed."""
    url = RSS_BY_HANDLE.format(channel_id=channel_id)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [warn] RSS 조회 실패 ({channel_id}): {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(resp.text)
    videos = []
    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        link_el = entry.find("atom:link", ns)
        published_el = entry.find("atom:published", ns)
        if video_id_el is None:
            continue
        videos.append(
            {
                "video_id": video_id_el.text,
                "title": title_el.text if title_el is not None else "",
                "url": link_el.attrib.get("href", "") if link_el is not None else "",
                "published": published_el.text if published_el is not None else "",
            }
        )
    return videos


def main():
    channels = json.loads(CHANNELS_FILE.read_text())
    processed = set(json.loads(PROCESSED_FILE.read_text()))

    new_videos = []
    for ch in channels:
        name = ch["name"]
        handle = ch["handle"]
        print(f"채널 확인 중: {name} (@{handle})", file=sys.stderr)

        channel_id = resolve_channel_id(handle)
        if not channel_id:
            print(f"  [skip] 채널 ID 미확인: {handle}", file=sys.stderr)
            continue

        print(f"  채널 ID: {channel_id}", file=sys.stderr)
        videos = fetch_rss(channel_id)
        print(f"  RSS 영상 수: {len(videos)}", file=sys.stderr)

        for v in videos:
            if v["video_id"] not in processed:
                v["channel_name"] = name
                new_videos.append(v)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    print(f"\n총 새 영상: {len(new_videos)}개", file=sys.stderr)


if __name__ == "__main__":
    main()
