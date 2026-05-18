#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via search."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROCESSED_FILE = ROOT / "data" / "processed.json"

SEARCH_QUERIES = [
    "한국 증시 오늘",
    "국내 주식 시황",
    "코스피 코스닥 분석",
]
MAX_RESULTS = 3


def load_json(path):
    with open(path) as f:
        return json.load(f)


def search_videos(query, max_results):
    cmd = [
        "yt-dlp",
        "--no-check-certificate",
        "--flat-playlist",
        "--playlist-end", str(max_results),
        "--print", "%(id)s\t%(title)s\t%(webpage_url)s",
        "--no-warnings",
        f"ytsearch{max_results}:{query}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    videos = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            video_id, title, url = parts[0], parts[1], parts[2]
            # Skip live streams (titles that suggest ongoing live broadcast)
            if "[LIVE" in title.upper() or "LIVE]" in title.upper() or "라이브" in title:
                continue
            videos.append({"id": video_id, "title": title, "url": url, "query": query})
    return videos


def main():
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get("processed", []))

    seen_ids = set()
    new_videos = []

    for query in SEARCH_QUERIES:
        print(f"[검색] {query} ...", file=sys.stderr)
        try:
            videos = search_videos(query, MAX_RESULTS)
            for v in videos:
                if v["id"] not in processed_ids and v["id"] not in seen_ids:
                    seen_ids.add(v["id"])
                    new_videos.append(v)
                    print(f"  [새 영상] {v['title']} ({v['id']})", file=sys.stderr)
        except Exception as e:
            print(f"  [오류] {query}: {e}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
