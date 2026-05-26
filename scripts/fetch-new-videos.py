#!/usr/bin/env python3
"""
Fetch new videos from Korean stock market YouTube channels.
Uses yt-dlp for channel video discovery (bypasses SSL restrictions).
Outputs JSON list of new (unprocessed) videos to stdout.
"""

import json
import ssl
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"
PROCESSED_FILE = DATA_DIR / "processed.json"

# Bypass proxy SSL certificate issues in cloud environments
ssl._create_default_https_context = ssl._create_unverified_context


def load_json(path, default):
    p = Path(path)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return default


def fetch_channel_videos(channel_url, channel_name, max_videos=8):
    try:
        import yt_dlp
    except ImportError:
        print("  [ERROR] yt-dlp not installed. Run: pip install yt-dlp", file=sys.stderr)
        return []

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "playlist_items": f"1-{max_videos}",
        "ignoreerrors": True,
        "nocheckcertificate": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if not info:
                return []
            videos = []
            for entry in info.get("entries", []):
                if not entry:
                    continue
                video_id = entry.get("id", "")
                title = entry.get("title", "제목 없음")
                published = entry.get("upload_date", "")
                if published and len(published) == 8:
                    published = f"{published[:4]}-{published[4:6]}-{published[6:]}"
                url = f"https://www.youtube.com/watch?v={video_id}"
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "published": published,
                    "url": url,
                    "channel_name": channel_name,
                })
            return videos
    except Exception as e:
        print(f"  [WARN] Failed to fetch {channel_url}: {e}", file=sys.stderr)
        return []


def main():
    channels = load_json(CHANNELS_FILE, [])
    processed_ids = set(load_json(PROCESSED_FILE, []))

    new_videos = []
    for ch in channels:
        print(f"Checking: {ch['name']} ({ch['channel_url']})", file=sys.stderr)
        videos = fetch_channel_videos(ch["channel_url"], ch["name"])
        for v in videos:
            if v["video_id"] not in processed_ids:
                new_videos.append(v)
                print(f"  NEW: [{v['video_id']}] {v['title'][:70]}", file=sys.stderr)
            else:
                print(f"  SKIP (processed): {v['video_id']}", file=sys.stderr)

    print(f"\nTotal new videos: {len(new_videos)}", file=sys.stderr)
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
