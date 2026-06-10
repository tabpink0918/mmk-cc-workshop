#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels."""

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def fetch_channel_videos(channel_url, max_videos=3):
    """Use yt-dlp to list recent videos from a channel."""
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--playlist-end", str(max_videos),
        "--print", '%(id)s\t%(title)s\t%(upload_date)s',
        "--no-warnings",
        "--quiet",
        "--no-check-certificates",
        channel_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    videos = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            video_id = parts[0]
            title = parts[1]
            upload_date = parts[2] if len(parts) > 2 else ""
            videos.append({
                "id": video_id,
                "title": title,
                "upload_date": upload_date,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })
    return videos


def main():
    channels_data = load_json(CHANNELS_FILE)
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed_video_ids", []))

    max_videos = channels_data.get("max_videos_per_channel", 3)
    new_videos = []

    for channel in channels_data["channels"]:
        print(f"[채널 확인] {channel['name']}: {channel['url']}", file=sys.stderr)
        try:
            videos = fetch_channel_videos(channel["url"], max_videos)
            for v in videos:
                if v["id"] not in processed_ids:
                    v["channel_name"] = channel["name"]
                    new_videos.append(v)
                    print(f"  새 영상: {v['title']} ({v['id']})", file=sys.stderr)
        except subprocess.TimeoutExpired:
            print(f"  타임아웃: {channel['name']}", file=sys.stderr)
        except Exception as e:
            print(f"  오류: {channel['name']} - {e}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0 if new_videos else 1


if __name__ == "__main__":
    sys.exit(main())
