#!/usr/bin/env python3
"""
한국 증시 YouTube 채널에서 최신 영상을 가져와 새 영상 목록을 출력합니다.
output: JSON array of new video objects to stdout
"""

import json
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

MAX_VIDEOS_PER_CHANNEL = 3  # 채널당 최근 N개 영상 확인


def load_json(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def get_recent_videos(channel_url, max_count=MAX_VIDEOS_PER_CHANNEL):
    """yt-dlp로 채널 최신 영상 목록 가져오기"""
    cmd = [
        "python3", "-m", "yt_dlp",
        "--no-check-certificate",
        "--flat-playlist",
        "--playlist-end", str(max_count),
        "--print", '%(id)s\t%(title)s\t%(url)s',
        "--no-warnings",
        "--quiet",
        channel_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        videos = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                vid_id = parts[0]
                title = parts[1]
                url = parts[2] if len(parts) > 2 else f"https://www.youtube.com/watch?v={vid_id}"
                if vid_id and not vid_id.startswith("http"):
                    videos.append({"id": vid_id, "title": title, "url": url})
        return videos
    except Exception as e:
        print(f"[WARN] 채널 조회 실패 {channel_url}: {e}", file=sys.stderr)
        return []


def main():
    channels = load_json(CHANNELS_FILE)
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed_video_ids", []))

    new_videos = []
    for ch in channels:
        ch_name = ch.get("name", "")
        ch_url = ch.get("channel_url", "")
        print(f"[INFO] 채널 확인: {ch_name} ({ch_url})", file=sys.stderr)
        videos = get_recent_videos(ch_url)
        for v in videos:
            if v["id"] not in processed_ids:
                v["channel_name"] = ch_name
                new_videos.append(v)
                print(f"  [NEW] {v['title']} (id={v['id']})", file=sys.stderr)
            else:
                print(f"  [SKIP] {v['title']} (이미 처리됨)", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
