#!/usr/bin/env python3
"""한국 증시 YouTube 채널에서 새 영상을 확인하는 스크립트."""

import json
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHANNELS_FILE = ROOT / "data" / "channels.json"
PROCESSED_FILE = ROOT / "data" / "processed.json"

LOOKBACK_DAYS = 2


def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def load_processed() -> set:
    if PROCESSED_FILE.exists():
        data = json.loads(PROCESSED_FILE.read_text())
        return set(data.get("processed", []))
    return set()


def load_channels() -> list:
    data = json.loads(CHANNELS_FILE.read_text())
    return data.get("channels", [])


def fetch_channel_videos(channel_id: str, ctx) -> list:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        content = resp.read()
    except Exception as e:
        print(f"  ⚠️  RSS 피드 가져오기 실패: {e}", file=sys.stderr)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = ET.fromstring(content)
    videos = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    for entry in root.findall("atom:entry", ns):
        vid_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        link_el = entry.find("atom:link", ns)

        if vid_id_el is None or title_el is None:
            continue

        vid_id = vid_id_el.text
        title = title_el.text or ""
        published_str = published_el.text if published_el is not None else ""
        url = link_el.get("href", f"https://www.youtube.com/watch?v={vid_id}") if link_el is not None else f"https://www.youtube.com/watch?v={vid_id}"

        # Parse published date
        try:
            pub_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except Exception:
            pub_dt = datetime.now(timezone.utc)

        if pub_dt < cutoff:
            continue

        videos.append({
            "video_id": vid_id,
            "title": title,
            "url": url,
            "published": published_str[:10] if published_str else "",
        })

    return videos


def main():
    processed = load_processed()
    channels = load_channels()
    ctx = get_ssl_context()

    new_videos = []
    for ch in channels:
        print(f"📡 {ch['name']} 채널 확인 중...", file=sys.stderr)
        videos = fetch_channel_videos(ch["channel_id"], ctx)
        for v in videos:
            if v["video_id"] not in processed:
                v["channel"] = ch["name"]
                new_videos.append(v)
                print(f"  ✅ 새 영상: [{v['published']}] {v['title']}", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    print(f"\n총 {len(new_videos)}개의 새 영상 발견", file=sys.stderr)


if __name__ == "__main__":
    main()
