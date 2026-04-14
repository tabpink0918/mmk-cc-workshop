#!/usr/bin/env python3
"""
한국 증시 유튜브 채널 새 영상 확인 스크립트

사용법:
    python3 scripts/fetch-new-videos.py

출력:
    새 영상 정보를 JSON 형식으로 stdout에 출력
    각 영상에 대해 mmk youtube transcript 시도 후 결과 포함
"""

import json
import os
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 프로젝트 루트 경로
ROOT = Path(__file__).parent.parent
CHANNELS_FILE = ROOT / "data" / "channels.json"
PROCESSED_FILE = ROOT / "data" / "processed.json"

# 새 영상 기준: 최근 N시간 이내 업로드
HOURS_THRESHOLD = 24

YOUTUBE_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def load_channels():
    """channels.json에서 채널 목록 로드"""
    if not CHANNELS_FILE.exists():
        print(f"[ERROR] channels.json not found: {CHANNELS_FILE}", file=sys.stderr)
        return []
    with open(CHANNELS_FILE) as f:
        return json.load(f)


def load_processed():
    """processed.json에서 이미 처리된 video_id 목록 로드"""
    if not PROCESSED_FILE.exists():
        return []
    with open(PROCESSED_FILE) as f:
        return json.load(f)


def fetch_channel_rss(channel_id):
    """YouTube RSS 피드에서 최신 영상 목록 가져오기"""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; mmk-workshop/1.0)"},
        )
        response = urllib.request.urlopen(req, timeout=15)
        xml_content = response.read()
        root = ET.fromstring(xml_content)

        videos = []
        entries = root.findall("atom:entry", YOUTUBE_NS)

        for entry in entries:
            video_id_el = entry.find("yt:videoId", YOUTUBE_NS)
            title_el = entry.find("atom:title", YOUTUBE_NS)
            published_el = entry.find("atom:published", YOUTUBE_NS)
            link_el = entry.find("atom:link", YOUTUBE_NS)
            description_el = entry.find(".//media:description", YOUTUBE_NS)

            if video_id_el is None or title_el is None:
                continue

            video_id = video_id_el.text
            title = title_el.text
            published_str = published_el.text if published_el is not None else ""
            url = (
                link_el.get("href", f"https://www.youtube.com/watch?v={video_id}")
                if link_el is not None
                else f"https://www.youtube.com/watch?v={video_id}"
            )
            description = description_el.text if description_el is not None else ""

            # 발행 시간 파싱
            published_dt = None
            if published_str:
                try:
                    published_dt = datetime.fromisoformat(
                        published_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            videos.append(
                {
                    "video_id": video_id,
                    "title": title,
                    "url": url,
                    "published": published_str,
                    "published_dt": published_dt,
                    "description": (description or "")[:500],
                }
            )

        return videos
    except Exception as e:
        print(f"[ERROR] RSS fetch failed for channel {channel_id}: {e}", file=sys.stderr)
        return []


def is_new_video(video, processed_ids, hours_threshold=HOURS_THRESHOLD):
    """영상이 새 영상인지 확인 (처리되지 않았고 최근 N시간 이내)"""
    if video["video_id"] in processed_ids:
        return False

    if video["published_dt"] is None:
        return True  # 시간 정보가 없으면 새 영상으로 간주

    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=hours_threshold)
    return video["published_dt"] >= threshold


def get_transcript_mmk(url):
    """mmk youtube transcript 명령어로 자막 추출"""
    print(f"  [INFO] mmk youtube transcript 시도: {url}", file=sys.stderr)
    try:
        result = subprocess.run(
            ["mmk", "youtube", "transcript", url],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            print(f"  [OK] 자막 추출 성공 ({len(result.stdout)} chars)", file=sys.stderr)
            return result.stdout.strip()
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            print(f"  [WARN] mmk transcript 실패: {error_msg[:100]}", file=sys.stderr)
            return None
    except subprocess.TimeoutExpired:
        print("  [WARN] mmk transcript timeout", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("  [WARN] mmk CLI not found", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [WARN] mmk transcript 오류: {e}", file=sys.stderr)
        return None


def get_metadata_mmk(url):
    """mmk youtube metadata 명령어로 메타데이터 추출"""
    try:
        result = subprocess.run(
            ["mmk", "youtube", "metadata", url, "-o", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except Exception:
        return None


def main():
    print("[INFO] 한국 증시 유튜브 채널 새 영상 확인 시작", file=sys.stderr)

    channels = load_channels()
    if not channels:
        print("[]")
        return

    processed_ids = set(load_processed())
    print(f"[INFO] 채널 수: {len(channels)}, 처리된 영상 수: {len(processed_ids)}", file=sys.stderr)

    new_videos = []

    for channel in channels:
        name = channel["name"]
        channel_id = channel["channel_id"]
        print(f"\n[INFO] 채널 확인: {name} ({channel_id})", file=sys.stderr)

        videos = fetch_channel_rss(channel_id)
        print(f"  RSS에서 {len(videos)}개 영상 확인", file=sys.stderr)

        for video in videos:
            if is_new_video(video, processed_ids):
                print(f"  [NEW] {video['video_id']}: {video['title'][:60]}", file=sys.stderr)

                # mmk youtube transcript 시도
                transcript = get_transcript_mmk(video["url"])

                # 결과 구성
                video_info = {
                    "video_id": video["video_id"],
                    "channel_name": name,
                    "channel_id": channel_id,
                    "title": video["title"],
                    "url": video["url"],
                    "published": video["published"],
                    "description": video["description"],
                    "transcript": transcript,
                    "transcript_available": transcript is not None,
                }

                # 처리된 목록에 추가 (중복 방지)
                processed_ids.add(video["video_id"])
                new_videos.append(video_info)

    print(f"\n[INFO] 새 영상 총 {len(new_videos)}개 발견", file=sys.stderr)

    # JSON 출력
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
