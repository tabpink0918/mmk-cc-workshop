#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels by scraping channel pages."""

import json
import sys
import re
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).parent.parent
CHANNELS_FILE = REPO_ROOT / "data" / "channels.json"
PROCESSED_FILE = REPO_ROOT / "data" / "processed.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# Only include videos within this many days (relative time text heuristic)
MAX_DAYS = 3


def is_recent(time_text: str) -> bool:
    """Return True if time_text suggests the video was posted within MAX_DAYS."""
    t = time_text.lower()
    if not t:
        return True  # unknown → include
    if "min" in t or "hour" in t or "시간" in t or "분" in t:
        return True
    if "h ago" in t:
        return True
    # "Xd ago" or "X일 전"
    m = re.match(r"(\d+)\s*(?:d\s*ago|일\s*전)", t)
    if m:
        return int(m.group(1)) <= MAX_DAYS
    # "X days ago"
    m2 = re.match(r"(\d+)\s*days?\s*ago", t)
    if m2:
        return int(m2.group(1)) <= MAX_DAYS
    # week/month/year → too old
    if any(w in t for w in ["week", "month", "year", "주", "달", "년"]):
        return False
    return True


def get_channel_videos(channel_url: str, channel_name: str) -> list[dict]:
    try:
        r = requests.get(channel_url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"  [WARN] Failed to fetch {channel_name}: {e}", file=sys.stderr)
        return []

    m = re.search(r"var ytInitialData = ({.*?});</script>", r.text, re.DOTALL)
    if not m:
        print(f"  [WARN] ytInitialData not found for {channel_name}", file=sys.stderr)
        return []

    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON parse error for {channel_name}: {e}", file=sys.stderr)
        return []

    tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
    videos = []

    for tab in tabs:
        content = tab.get("tabRenderer", {}).get("content", {})
        grid = content.get("richGridRenderer", {}).get("contents", [])
        if not grid:
            continue
        for item in grid:
            lvm = item.get("richItemRenderer", {}).get("content", {}).get("lockupViewModel", {})
            if not lvm:
                continue

            # Extract video ID from thumbnail URL
            thumb_sources = (
                lvm.get("contentImage", {})
                .get("thumbnailViewModel", {})
                .get("image", {})
                .get("sources", [])
            )
            vid_id = None
            for src in thumb_sources:
                m2 = re.search(r"/vi/([^/]+)/", src.get("url", ""))
                if m2:
                    vid_id = m2.group(1)
                    break

            # Extract title
            meta = lvm.get("metadata", {}).get("lockupMetadataViewModel", {})
            title = meta.get("title", {}).get("content", "")

            # Extract publish time text
            rows = meta.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
            time_text = ""
            for row in rows:
                for part in row.get("metadataParts", []):
                    t = part.get("text", {}).get("content", "")
                    if any(
                        x in t.lower()
                        for x in ["ago", "전", "시간", "분", "일", "week", "month", "year"]
                    ):
                        time_text = t
                        break

            if vid_id and title and is_recent(time_text):
                videos.append(
                    {
                        "video_id": vid_id,
                        "title": title,
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                        "time_text": time_text,
                        "channel_name": channel_name,
                    }
                )
        break  # only process the first tab with a grid

    return videos


def main():
    channels_data = json.loads(CHANNELS_FILE.read_text())
    processed_data = json.loads(PROCESSED_FILE.read_text())
    processed_ids = set(processed_data.get("processed", []))

    new_videos = []
    for ch in channels_data["channels"]:
        print(f"Checking {ch['name']}…", file=sys.stderr)
        videos = get_channel_videos(ch["url"] + "/videos", ch["name"])
        for v in videos:
            if v["video_id"] not in processed_ids:
                new_videos.append(v)
                print(f"  NEW [{v['time_text']}] {v['title'][:60]}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
