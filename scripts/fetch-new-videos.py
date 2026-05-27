#!/usr/bin/env python3
"""
한국 증시 유튜브 채널에서 새 영상을 확인하는 스크립트.
각 채널의 최신 N개 영상을 가져와 processed.json에 없는 새 영상을 출력한다.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CHANNELS_FILE = REPO_ROOT / "data" / "channels.json"
PROCESSED_FILE = REPO_ROOT / "data" / "processed.json"
VIDEOS_PER_CHANNEL = 5


def get_recent_videos(channel_url: str, count: int) -> list[dict]:
    cmd = [
        "yt-dlp",
        "--no-check-certificates",
        "--flat-playlist",
        f"--playlist-end={count}",
        "--print", "%(id)s\t%(title)s\t%(duration)s\t%(webpage_url)s",
        "--no-warnings",
        channel_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        videos = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 4:
                vid_id, title, duration, url = parts[0], parts[1], parts[2], parts[3]
                videos.append({"id": vid_id, "title": title, "duration": duration, "url": url})
        return videos
    except subprocess.TimeoutExpired:
        print(f"  timeout fetching {channel_url}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  error fetching {channel_url}: {e}", file=sys.stderr)
        return []


def main():
    channels = json.loads(CHANNELS_FILE.read_text())
    processed = json.loads(PROCESSED_FILE.read_text())
    processed_ids = set(processed.get("processed_ids", []))

    new_videos = []
    for channel in channels:
        print(f"채널 확인 중: {channel['name']} ...", file=sys.stderr)
        videos = get_recent_videos(channel["url"], VIDEOS_PER_CHANNEL)
        for v in videos:
            if v["id"] not in processed_ids:
                v["channel_name"] = channel["name"]
                v["channel_handle"] = channel["handle"]
                new_videos.append(v)
                print(f"  새 영상: {v['title'][:60]}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    print(f"\n총 {len(new_videos)}개 새 영상 발견", file=sys.stderr)


if __name__ == "__main__":
    main()
