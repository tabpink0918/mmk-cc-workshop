#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels."""

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHANNELS_FILE = BASE_DIR / "data" / "channels.json"
PROCESSED_FILE = BASE_DIR / "data" / "processed.json"

MAX_AGE_HOURS = 48
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def parse_relative_time_hours(text: str) -> float | None:
    """Parse Korean relative time text to approximate hours ago."""
    if not text:
        return None
    text = text.strip()
    m = re.match(r"(\d+)분\s*전", text)
    if m:
        return int(m.group(1)) / 60
    m = re.match(r"(\d+)시간\s*전", text)
    if m:
        return int(m.group(1))
    m = re.match(r"(\d+)일\s*전", text)
    if m:
        return int(m.group(1)) * 24
    m = re.match(r"(\d+)주\s*전", text)
    if m:
        return int(m.group(1)) * 24 * 7
    return None


def fetch_ytInitialData(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    m = re.search(r"ytInitialData\s*=\s*", html)
    if not m:
        return {}
    start = m.end()
    depth = 0
    end = start
    for i in range(start, min(start + 3_000_000, len(html))):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return json.loads(html[start:end])


def fetch_channel_videos(handle: str, channel_name: str) -> list[dict]:
    url = f"https://www.youtube.com/{handle}/videos"
    try:
        data = fetch_ytInitialData(url)
    except Exception as e:
        print(f"  [warn] failed to fetch {handle}: {e}", file=sys.stderr)
        return []

    tabs = (
        data.get("contents", {})
        .get("twoColumnBrowseResultsRenderer", {})
        .get("tabs", [])
    )
    videos = []
    for tab in tabs:
        tr = tab.get("tabRenderer", {})
        if tr.get("title") not in ("동영상", "Videos"):
            continue
        grid_contents = (
            tr.get("content", {}).get("richGridRenderer", {}).get("contents", [])
        )
        for item in grid_contents:
            v = (
                item.get("richItemRenderer", {})
                .get("content", {})
                .get("videoRenderer", {})
            )
            if not v:
                continue
            vid_id = v.get("videoId", "")
            title_runs = v.get("title", {}).get("runs", [])
            title = title_runs[0].get("text", "") if title_runs else ""
            pub_text = v.get("publishedTimeText", {}).get("simpleText", "")
            hours_ago = parse_relative_time_hours(pub_text)

            if hours_ago is not None and hours_ago > MAX_AGE_HOURS:
                break  # videos are chronological; stop when too old

            videos.append({
                "video_id": vid_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "channel_name": channel_name,
                "published_text": pub_text,
                "hours_ago": hours_ago,
            })
        break

    return videos


def main():
    channels = json.loads(CHANNELS_FILE.read_text())
    processed = set(json.loads(PROCESSED_FILE.read_text()))

    new_videos = []

    for ch in channels:
        handle = ch["handle"]
        name = ch["name"]
        print(f"Checking channel: {name} ({handle})", file=sys.stderr)

        try:
            videos = fetch_channel_videos(handle, name)
        except Exception as e:
            print(f"  [error] {e}", file=sys.stderr)
            continue
        time.sleep(1.5)

        for v in videos:
            vid = v["video_id"]
            if vid in processed:
                print(f"  [skip] {vid}", file=sys.stderr)
                continue
            new_videos.append(v)
            print(
                f"  [new] {v['title'][:60]} ({v.get('published_text','?')})",
                file=sys.stderr,
            )

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
