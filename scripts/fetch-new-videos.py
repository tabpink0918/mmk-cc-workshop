"""한국 증시 유튜브 채널에서 새 영상을 확인하는 스크립트.

YouTube RSS 피드를 통해 각 채널의 최신 영상을 수집하고,
data/processed.json에 없는 신규 영상만 JSON으로 출력합니다.
"""

import json
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

# 한국 증시 유튜브 채널 설정
CHANNELS = [
    {
        "name": "한경글로벌마켓",
        "channel_id": "UCWskYkV4c4S9D__rsfOl2JA",
        "keywords": ["개장전요것만", "빈난새", "월스트리트나우", "김현석", "빈틈없이월가"],
    },
    {
        "name": "한국경제TV",
        "channel_id": "UCF8AeLlUbEpKju6v1H6p8Eg",
        "keywords": ["당잠사"],
    },
    {
        "name": "증시각도기TV",
        "channel_id": "UCdOjVxkj5JA0iDu3_xcsTyQ",
        "keywords": [],  # 빈 배열 = 전체 수집
    },
]

PROCESSED_FILE = Path(__file__).parent.parent / "data" / "processed.json"


def load_processed():
    """처리 완료된 video_id 목록을 로드한다."""
    if not PROCESSED_FILE.exists():
        return []
    try:
        with open(PROCESSED_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []


def fetch_channel_rss(channel_id, channel_name):
    """YouTube RSS 피드에서 채널 영상 목록을 가져온다."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (compatible; RSS reader)"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        print(f"[ERROR] {channel_name} RSS 수집 실패: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR] {channel_name} 예외 발생: {e}", file=sys.stderr)
        return None


def parse_rss_entries(xml_data, channel_name, keywords):
    """RSS XML을 파싱하여 영상 목록을 반환한다."""
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"[ERROR] {channel_name} XML 파싱 실패: {e}", file=sys.stderr)
        return []

    videos = []
    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)

        if video_id_el is None or title_el is None:
            continue

        video_id = video_id_el.text or ""
        title = title_el.text or ""
        published = published_el.text if published_el is not None else ""
        url = f"https://www.youtube.com/watch?v={video_id}"

        # Shorts 제외
        title_lower = title.lower()
        if "#shorts" in title_lower or "shorts" == title_lower.strip():
            continue

        # 채널별 키워드 필터링 (키워드 있는 경우만)
        if keywords:
            if not any(kw.lower() in title_lower for kw in keywords):
                continue

        videos.append(
            {
                "video_id": video_id,
                "title": title,
                "channel_name": channel_name,
                "published": published,
                "url": url,
            }
        )

    return videos


def main():
    processed = load_processed()
    # processed.json 항목은 문자열(video_id) 또는 딕셔너리일 수 있음
    processed_ids = set()
    for item in processed:
        if isinstance(item, str):
            processed_ids.add(item)
        elif isinstance(item, dict):
            processed_ids.add(item.get("video_id", ""))

    new_videos = []

    for channel in CHANNELS:
        name = channel["name"]
        channel_id = channel["channel_id"]
        keywords = channel["keywords"]

        print(f"[INFO] {name} 채널 RSS 확인 중...", file=sys.stderr)
        xml_data = fetch_channel_rss(channel_id, name)
        if not xml_data:
            continue

        videos = parse_rss_entries(xml_data, name, keywords)
        print(f"[INFO] {name}: 키워드 매칭 영상 {len(videos)}개", file=sys.stderr)

        for video in videos:
            vid = video["video_id"]
            if vid in processed_ids:
                print(f"[SKIP] {video['title'][:50]} (처리됨)", file=sys.stderr)
            else:
                print(f"[NEW]  {video['title'][:50]}", file=sys.stderr)
                new_videos.append(video)

    print(f"\n[RESULT] 새 영상 {len(new_videos)}개 발견", file=sys.stderr)
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return new_videos


if __name__ == "__main__":
    main()
