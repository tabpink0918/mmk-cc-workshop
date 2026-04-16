#!/usr/bin/env python3
"""
한국 증시 유튜브 채널에서 새 영상을 확인하는 스크립트
Fetch new videos from Korean stock market YouTube channels
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

# 최근 N일 이내 영상만 확인 (default: 3일)
DAYS_LOOKBACK = 3


def load_channels():
    with open(CHANNELS_FILE) as f:
        return json.load(f)["channels"]


def load_processed():
    with open(PROCESSED_FILE) as f:
        return set(json.load(f)["processed"])


def fetch_channel_videos(channel: dict, max_videos: int = 10) -> list:
    """yt-dlp으로 채널의 최신 영상 목록을 가져옴"""
    handle = channel["handle"]
    name = channel["name"]

    print(f"  채널 확인 중: {name} ({handle})", flush=True)

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--no-check-certificate",
                "--flat-playlist",
                f"--playlist-end", str(max_videos),
                "--print", "%(id)s|%(title)s|%(upload_date)s|%(webpage_url)s",
                "--no-warnings",
                f"https://www.youtube.com/{handle}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) >= 2:
                video_id = parts[0]
                title = parts[1] if len(parts) > 1 else "제목 없음"
                upload_date = parts[2] if len(parts) > 2 else "NA"
                raw_url = parts[3] if len(parts) > 3 else ""
                # yt-dlp sometimes returns "NA|actual_url" format
                if raw_url and "NA|" in raw_url:
                    raw_url = raw_url.split("NA|", 1)[-1]
                url = raw_url if raw_url and raw_url != "NA" else f"https://www.youtube.com/watch?v={video_id}"

                videos.append({
                    "id": video_id,
                    "title": title,
                    "upload_date": upload_date,
                    "url": url,
                    "channel": name,
                    "channel_handle": handle,
                })

        if result.returncode != 0 and not videos:
            print(f"    경고: {name} 채널 접근 실패 - {result.stderr[:100]}", flush=True)

        return videos

    except subprocess.TimeoutExpired:
        print(f"    오류: {name} 채널 타임아웃", flush=True)
        return []
    except Exception as e:
        print(f"    오류: {name} 채널 처리 중 예외 발생 - {e}", flush=True)
        return []


def is_recent(upload_date: str, days: int = DAYS_LOOKBACK) -> bool:
    """영상이 최근 N일 이내인지 확인"""
    if upload_date == "NA" or not upload_date:
        # 날짜 정보가 없으면 최신으로 간주
        return True

    try:
        if len(upload_date) == 8:
            video_date = datetime.strptime(upload_date, "%Y%m%d")
        else:
            return True

        cutoff = datetime.now() - timedelta(days=days)
        return video_date >= cutoff
    except Exception:
        return True


def main():
    print("=== 한국 증시 유튜브 채널 새 영상 확인 ===\n", flush=True)
    print(f"기준: 최근 {DAYS_LOOKBACK}일 이내 미처리 영상\n", flush=True)

    channels = load_channels()
    processed = load_processed()

    new_videos = []

    for channel in channels:
        videos = fetch_channel_videos(channel)

        channel_new = []
        for video in videos:
            if video["id"] not in processed:
                if is_recent(video["upload_date"]):
                    channel_new.append(video)
                    new_videos.append(video)
                else:
                    print(f"    건너뜀 (오래된 영상): {video['title'][:40]}", flush=True)

        if channel_new:
            print(f"    새 영상 {len(channel_new)}개 발견!", flush=True)
            for v in channel_new:
                print(f"      - [{v['id']}] {v['title'][:60]}", flush=True)
        else:
            print(f"    새 영상 없음", flush=True)
        print()

    print(f"\n=== 결과 ===", flush=True)
    print(f"총 새 영상: {len(new_videos)}개", flush=True)

    if new_videos:
        print("\n처리할 영상 목록:")
        for i, v in enumerate(new_videos, 1):
            print(f"  {i}. [{v['channel']}] {v['title'][:60]}")
            print(f"     URL: {v['url']}")

    # 결과를 JSON으로 출력 (파이프로 사용 가능)
    output = {
        "new_videos": new_videos,
        "total": len(new_videos),
        "timestamp": datetime.now().isoformat(),
    }

    with open("/tmp/new_videos.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: /tmp/new_videos.json", flush=True)
    return 0 if new_videos else 1


if __name__ == "__main__":
    sys.exit(main())
