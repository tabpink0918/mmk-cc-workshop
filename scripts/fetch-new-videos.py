#!/usr/bin/env python3
"""
한국 증시 YouTube 채널에서 새 영상을 확인하는 스크립트.
scrapetube를 사용하여 최근 영상을 가져오고, processed.json과 비교하여 새 영상만 출력합니다.
"""

import json
import sys
from pathlib import Path

try:
    import scrapetube
except ImportError:
    print("[ERROR] scrapetube is not installed. Run: pip install scrapetube", file=sys.stderr)
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

MAX_VIDEOS_PER_CHANNEL = 5


def load_processed() -> set:
    if not PROCESSED_FILE.exists():
        return set()
    with open(PROCESSED_FILE) as f:
        data = json.load(f)
    return set(data.get("processed_video_ids", []))


def get_text(obj) -> str:
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        runs = obj.get("runs", [])
        if runs:
            return "".join(r.get("text", "") for r in runs)
        simple = obj.get("simpleText", "")
        if simple:
            return simple
    return ""


def fetch_channel_videos(channel_id: str, channel_name: str) -> list[dict]:
    videos = []
    try:
        raw_videos = scrapetube.get_channel(channel_id, limit=MAX_VIDEOS_PER_CHANNEL)
        for v in raw_videos:
            video_id = v.get("videoId", "")
            if not video_id:
                continue
            title = get_text(v.get("title", ""))
            description = get_text(v.get("descriptionSnippet", ""))
            published = get_text(v.get("publishedTimeText", ""))
            duration = get_text(v.get("lengthText", ""))
            views = get_text(v.get("viewCountText", ""))

            videos.append({
                "video_id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "description": description,
                "published": published,
                "duration": duration,
                "views": views,
                "channel_name": channel_name,
            })
    except Exception as e:
        print(f"[WARN] 채널 조회 실패 (channel_id={channel_id}): {e}", file=sys.stderr)
    return videos


def main():
    channels_data = json.loads(CHANNELS_FILE.read_text())
    channels = channels_data.get("channels", [])
    processed = load_processed()

    new_videos = []
    for ch in channels:
        channel_id = ch["channel_id"]
        channel_name = ch["name"]
        videos = fetch_channel_videos(channel_id, channel_name)
        for v in videos:
            if v["video_id"] not in processed:
                new_videos.append(v)

    result = {"new_videos": new_videos, "count": len(new_videos)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
