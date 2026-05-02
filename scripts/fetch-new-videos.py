#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via yt-dlp."""

import json
import subprocess
import sys
from pathlib import Path

# Korean stock market / finance YouTube channels
CHANNELS = [
    ("삼프로TV", "https://www.youtube.com/@3PROTV/videos"),
    ("슈카월드", "https://www.youtube.com/@syukaworld/videos"),
    ("한국경제신문", "https://www.youtube.com/@hankyungTV/videos"),
]

PROCESSED_PATH = Path(__file__).parent.parent / "data" / "processed.json"
VIDEOS_PER_CHANNEL = 5


def load_processed() -> set:
    if PROCESSED_PATH.exists():
        data = json.loads(PROCESSED_PATH.read_text())
        return set(data.get("processed_video_ids", []))
    return set()


def fetch_channel_videos(channel_name: str, channel_url: str) -> list[dict]:
    cmd = [
        "yt-dlp",
        "--no-check-certificate",
        "--flat-playlist",
        f"--playlist-end={VIDEOS_PER_CHANNEL}",
        "--dump-json",
        "--quiet",
        channel_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print(f"  [WARN] {channel_name} 타임아웃", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [WARN] {channel_name} 실패: {e}", file=sys.stderr)
        return []

    videos = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        video_id = data.get("id", "")
        if not video_id:
            continue
        description = data.get("description") or ""
        videos.append({
            "video_id": video_id,
            "title": data.get("title", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "description": description[:800],
            "duration": data.get("duration_string", ""),
            "channel": channel_name,
        })
    return videos


def main():
    processed = load_processed()
    new_videos = []

    for channel_name, channel_url in CHANNELS:
        print(f"채널 확인 중: {channel_name}...")
        videos = fetch_channel_videos(channel_name, channel_url)
        for v in videos:
            if v["video_id"] not in processed:
                new_videos.append(v)
                print(f"  [NEW] {v['title'][:60]} ({v['video_id']})")

    if not new_videos:
        print("새 영상 없음.")
    else:
        print(f"\n총 {len(new_videos)}개의 새 영상 발견.")

    print("\n__NEW_VIDEOS_JSON__")
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
