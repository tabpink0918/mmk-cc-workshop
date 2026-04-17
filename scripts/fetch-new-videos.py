#!/usr/bin/env python3
"""
Korean stock market YouTube channel new video checker.
Uses yt-dlp to fetch recent videos from channels and outputs
ones not yet in data/processed.json.
"""

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"
MAX_VIDEOS_PER_CHANNEL = 5


def load_json(path):
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def fetch_channel_videos(handle):
    """Fetch recent video IDs and titles from a YouTube channel via yt-dlp."""
    url = f"https://www.youtube.com/{handle}"
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--flat-playlist",
                "--print", "%(id)s\t%(title)s",
                "--playlist-items", f"1-{MAX_VIDEOS_PER_CHANNEL}",
                "--no-warnings",
                "--no-check-certificates",
                "--quiet",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        videos = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                video_id, title = parts
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                })
        return videos
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {url}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [Error] {url}: {e}", file=sys.stderr)
        return []


def main():
    channels = load_json(CHANNELS_FILE)
    processed = set(load_json(PROCESSED_FILE))

    new_videos = []

    for ch in channels:
        name = ch.get("name", "Unknown")
        handle = ch.get("handle", "")
        if not handle:
            continue
        print(f"채널 확인 중: {name} ({handle})", file=sys.stderr)

        videos = fetch_channel_videos(handle)
        for v in videos:
            if v["video_id"] not in processed:
                v["channel"] = name
                new_videos.append(v)
                print(f"  [NEW] {v['title']}", file=sys.stderr)
            else:
                print(f"  [SKIP] {v['title']}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
