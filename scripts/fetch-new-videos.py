#!/usr/bin/env python3
"""
한국 증시 YouTube 채널에서 새 영상을 확인하는 스크립트.
data/channels.json에 정의된 채널의 RSS 피드를 읽어 최근 48시간 이내 영상 중
data/processed.json에 없는 새 영상을 출력합니다.
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"
HOURS_WINDOW = 48

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

STOCK_KEYWORDS = [
    "주식", "증시", "코스피", "코스닥", "반도체", "2차전지", "투자", "매수", "매도",
    "주가", "종목", "ETF", "펀드", "경제", "금융", "증권", "삼성", "SK하이닉스",
    "에코프로", "조선", "AI", "인공지능", "달러", "환율", "금리", "채권",
]


def fetch_rss(channel_id: str) -> ET.Element | None:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return ET.fromstring(resp.read())
    except Exception as e:
        print(f"[WARN] RSS 가져오기 실패 ({channel_id}): {e}", file=sys.stderr)
        return None


def parse_published(dt_str: str) -> datetime:
    # Format: 2026-05-02T23:00:18+00:00
    return datetime.fromisoformat(dt_str).astimezone(timezone.utc)


def is_stock_related(title: str, description: str = "") -> bool:
    text = title + " " + description
    return any(kw in text for kw in STOCK_KEYWORDS)


def main():
    channels = json.loads(CHANNELS_FILE.read_text())["channels"]
    processed_ids = set(json.loads(PROCESSED_FILE.read_text())["processed"])

    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_WINDOW)
    new_videos = []

    for ch in channels:
        root = fetch_rss(ch["id"])
        if root is None:
            continue

        entries = root.findall("atom:entry", NS)
        for entry in entries:
            video_id = entry.findtext("yt:videoId", namespaces=NS)
            title = entry.findtext("atom:title", namespaces=NS) or ""
            link_el = entry.find("atom:link[@rel='alternate']", NS)
            url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"
            published_str = entry.findtext("atom:published", namespaces=NS) or ""
            desc_el = entry.find("media:group/media:description", NS)
            description = desc_el.text if desc_el is not None else ""

            if not video_id or not published_str:
                continue

            try:
                published = parse_published(published_str)
            except ValueError:
                continue

            if published < cutoff:
                continue

            if video_id in processed_ids:
                continue

            if not is_stock_related(title, description):
                print(f"[SKIP] 증시 무관 영상: {title}", file=sys.stderr)
                continue

            new_videos.append({
                "video_id": video_id,
                "title": title,
                "url": url,
                "channel": ch["name"],
                "published": published_str,
            })

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    print(f"\n[INFO] 새 영상 {len(new_videos)}개 발견", file=sys.stderr)


if __name__ == "__main__":
    main()
