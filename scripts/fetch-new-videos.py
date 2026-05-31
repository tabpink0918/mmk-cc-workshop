#!/usr/bin/env python3
"""한국 증시 유튜브 채널에서 최근 영상을 가져와 미처리 영상 목록을 출력합니다."""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

CHANNELS = [
    {"name": "삼프로TV", "channel_id": "UChlv4GSd7OQl3js-jkLOnFA"},
    {"name": "한국경제TV", "channel_id": "UCF8AeLlUbEpKju6v1H6p8Eg"},
    {"name": "삼성증권", "channel_id": "UCq7h8qFlHN5FL_T6waKZllw"},
]

# 증시·금융 관련 키워드 필터 (이 단어 중 하나도 없으면 제외)
FINANCE_KEYWORDS = [
    "증시", "코스피", "코스닥", "주식", "반도체", "삼성전자", "하이닉스",
    "투자", "펀드", "금리", "환율", "경제", "시황", "마감", "개장",
    "브리핑", "인터뷰", "장세", "수출", "IPO", "ETF", "채권", "원자재",
    "재테크", "삼프로", "주린이", "당잠사", "밸류업",
]

PROCESSED_FILE = Path(__file__).parent.parent / "data" / "processed.json"
DAYS_LOOKBACK = 3


def load_processed() -> set:
    if PROCESSED_FILE.exists():
        data = json.loads(PROCESSED_FILE.read_text())
        return set(data.get("processed_video_ids", []))
    return set()


def is_finance_related(title: str) -> bool:
    return any(kw in title for kw in FINANCE_KEYWORDS)


def fetch_channel_videos(channel_id: str) -> list[dict]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
    except Exception as e:
        print(f"[WARN] 채널 {channel_id} 피드 요청 실패: {e}", file=sys.stderr)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_LOOKBACK)
    videos = []
    for entry in root.findall("atom:entry", ns):
        video_id = entry.findtext("yt:videoId", namespaces=ns)
        title = entry.findtext("atom:title", namespaces=ns)
        published_str = entry.findtext("atom:published", namespaces=ns)
        if not (video_id and title and published_str):
            continue
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if published >= cutoff:
            videos.append({
                "video_id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "published": published_str,
            })
    return videos


def main():
    processed = load_processed()
    new_videos = []

    for ch in CHANNELS:
        videos = fetch_channel_videos(ch["channel_id"])
        for v in videos:
            if v["video_id"] not in processed and is_finance_related(v["title"]):
                v["channel"] = ch["name"]
                new_videos.append(v)

    # 최신순 정렬
    new_videos.sort(key=lambda x: x["published"], reverse=True)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0 if new_videos else 1


if __name__ == "__main__":
    sys.exit(main())
