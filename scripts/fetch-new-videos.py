#!/usr/bin/env python3
"""
YouTube 채널에서 새 영상을 확인하는 스크립트.
channels.json에 등록된 채널의 페이지를 크롤링하여
processed.json에 없는 새 영상만 JSON으로 출력합니다.
"""

import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

LOOKBACK_DAYS = 7

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def fetch_channel_videos(handle: str, channel_name: str) -> list[dict]:
    url = f"https://www.youtube.com/@{handle}/videos"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [WARN] 채널 페이지 조회 실패 ({handle}): {e}", file=sys.stderr)
        return []

    # ytInitialData에서 영상 목록 추출
    match = re.search(r"var ytInitialData\s*=\s*({.*?});\s*</script", raw, re.DOTALL)
    if not match:
        print(f"  [WARN] ytInitialData를 찾을 수 없음 ({handle})", file=sys.stderr)
        return []

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON 파싱 실패 ({handle}): {e}", file=sys.stderr)
        return []

    tabs = (
        data.get("contents", {})
        .get("twoColumnBrowseResultsRenderer", {})
        .get("tabs", [])
    )

    videos = []
    for tab in tabs:
        tr = tab.get("tabRenderer", {})
        items = (
            tr.get("content", {})
            .get("richGridRenderer", {})
            .get("contents", [])
        )
        for item in items:
            rich = item.get("richItemRenderer", {}).get("content", {})
            vm = rich.get("videoRenderer", {})
            if not vm.get("videoId"):
                continue

            video_id = vm["videoId"]
            title_data = vm.get("title", {})
            title = title_data.get("simpleText", "") or (
                title_data.get("runs", [{}])[0].get("text", "")
            )

            # 날짜: publishedTimeText 또는 publishDate
            pub_text = vm.get("publishedTimeText", {}).get("simpleText", "")

            videos.append(
                {
                    "video_id": video_id,
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "channel_name": channel_name,
                    "handle": handle,
                    "published_text": pub_text,
                }
            )

    return videos


def is_recent(published_text: str, days: int = LOOKBACK_DAYS) -> bool:
    """
    '3일 전', '1주 전', '2시간 전' 같은 상대 표현을 파싱하여
    LOOKBACK_DAYS 이내인지 확인합니다.
    """
    if not published_text:
        return True  # 날짜 없으면 새 영상으로 간주

    text = published_text.lower()

    # 시간/분/초 단위 → 확실히 최근
    if any(kw in text for kw in ["시간", "분 전", "초 전", "hour", "minute", "second"]):
        return True

    # 일 단위
    day_match = re.search(r"(\d+)\s*(?:일|day)", text)
    if day_match:
        return int(day_match.group(1)) <= days

    # 주 단위
    week_match = re.search(r"(\d+)\s*(?:주|week)", text)
    if week_match:
        return int(week_match.group(1)) * 7 <= days

    # 달/월/년 단위 → 오래된 영상
    if any(kw in text for kw in ["달", "개월", "월 전", "year", "month"]):
        return False

    return True  # 파싱 불가 → 일단 포함


def main():
    channels_data = json.loads(CHANNELS_FILE.read_text(encoding="utf-8"))
    processed_data = json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))
    processed_ids = set(processed_data.get("processed_video_ids", []))

    new_videos: list[dict] = []

    for ch in channels_data.get("channels", []):
        name = ch.get("name", "unknown")
        handle = ch.get("handle", "")
        if not handle:
            continue

        print(f"[INFO] 채널 확인 중: {name} (@{handle})", file=sys.stderr)
        videos = fetch_channel_videos(handle, name)
        print(f"  {len(videos)}개 영상 발견", file=sys.stderr)

        for v in videos:
            if v["video_id"] in processed_ids:
                print(f"  [SKIP] 이미 처리됨: {v['title'][:40]}", file=sys.stderr)
                continue
            if not is_recent(v.get("published_text", "")):
                print(f"  [SKIP] 오래된 영상: {v['title'][:40]}", file=sys.stderr)
                continue
            new_videos.append(v)
            print(
                f"  [NEW] {v['title'][:60]} ({v.get('published_text', '')})",
                file=sys.stderr,
            )

        time.sleep(0.5)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
