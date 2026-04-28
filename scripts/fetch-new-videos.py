#!/usr/bin/env python3
"""
한국 증시 유튜브 채널의 새 영상을 확인합니다.
yt-dlp를 사용하여 최신 영상 목록을 가져오고, processed.json에 없는 영상을 반환합니다.
"""
import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"
MAX_VIDEOS_PER_CHANNEL = 5


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_latest_videos(channel_url: str, max_count: int = MAX_VIDEOS_PER_CHANNEL) -> list[dict]:
    cmd = [
        "yt-dlp",
        "--no-warnings",
        "--no-check-certificate",
        "--flat-playlist",
        "--print", "%(id)s\t%(title)s\t%(upload_date)s",
        "--playlist-items", f"1:{max_count}",
        channel_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                video_id = parts[0].strip()
                title = parts[1].strip() if len(parts) > 1 else ""
                upload_date = parts[2].strip() if len(parts) > 2 else ""
                if video_id:
                    videos.append({
                        "video_id": video_id,
                        "title": title,
                        "upload_date": upload_date,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                    })
        return videos
    except subprocess.TimeoutExpired:
        print(f"  [WARNING] 타임아웃: {channel_url}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [WARNING] 영상 가져오기 실패: {e}", file=sys.stderr)
        return []


def main():
    channels_data = load_json(CHANNELS_FILE)
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed_video_ids", []))

    new_videos = []
    for ch in channels_data["channels"]:
        name = ch["name"]
        url = ch.get("url", "")
        print(f"[채널] {name} 확인 중...", file=sys.stderr)

        videos = fetch_latest_videos(url)
        for v in videos:
            if v["video_id"] not in processed_ids:
                v["channel_name"] = name
                new_videos.append(v)
                print(f"  [NEW] {v['title']} ({v['video_id']})", file=sys.stderr)
            else:
                print(f"  [SKIP] {v['title']} (이미 처리됨)", file=sys.stderr)

    if not new_videos:
        print("새 영상 없음", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
