#!/usr/bin/env python3
"""
한국 증시 유튜브 채널에서 최신 영상을 가져와 미처리 영상 목록을 출력합니다.
YouTube RSS 피드를 사용하므로 API 키가 필요 없습니다.
"""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.error

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

# 최근 며칠 이내 영상만 처리 (기본 7일)
DAYS_LIMIT = 7


def load_json(path):
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 2:
                import time; time.sleep(2 ** attempt)
                continue
            print(f"  [경고] RSS 피드 오류 (HTTP {e.code}): {url}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  [경고] RSS 피드 접근 실패: {e}", file=sys.stderr)
            return None
    return None


def parse_rss(xml_data, channel_name):
    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_LIMIT)

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"  [경고] XML 파싱 실패: {e}", file=sys.stderr)
        return videos

    for entry in root.findall("atom:entry", NS):
        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        link_el = entry.find("atom:link", NS)

        if video_id_el is None or title_el is None or published_el is None:
            continue

        video_id = video_id_el.text
        title = title_el.text or ""
        published_str = published_el.text or ""
        url = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

        # 날짜 파싱 (ISO 8601: 2024-01-15T10:00:00+00:00)
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if published >= cutoff:
            videos.append({
                "video_id": video_id,
                "title": title,
                "url": url,
                "published": published_str,
                "channel": channel_name,
            })

    return videos


def main():
    channels = load_json(CHANNELS_FILE)
    processed_ids = set(load_json(PROCESSED_FILE))

    print(f"채널 {len(channels)}개 확인 중... (최근 {DAYS_LIMIT}일 이내 영상)", file=sys.stderr)

    new_videos = []
    for ch in channels:
        channel_id = ch["channel_id"]
        name = ch["name"]
        print(f"  - {name} ({channel_id})", file=sys.stderr)

        xml_data = fetch_rss(channel_id)
        if xml_data is None:
            continue

        videos = parse_rss(xml_data, name)
        for v in videos:
            if v["video_id"] not in processed_ids:
                new_videos.append(v)

    print(f"\n새 영상 {len(new_videos)}개 발견", file=sys.stderr)
    # stdout에 JSON 출력 (호출자가 파싱 가능하도록)
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
