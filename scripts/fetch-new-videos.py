#!/usr/bin/env python3
"""
Fetch new YouTube videos from Korean stock market channels.
Outputs JSON list of new (unprocessed) videos.
"""
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS_FILE = os.path.join(BASE_DIR, "data", "channels.json")
PROCESSED_FILE = os.path.join(BASE_DIR, "data", "processed.json")


def load_processed():
    try:
        with open(PROCESSED_FILE) as f:
            data = json.load(f)
            if isinstance(data, dict):
                return set(data.get("processed", []))
            return set(data)
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def load_channels():
    with open(CHANNELS_FILE) as f:
        return json.load(f)


def fetch_channel_videos(channel_id, max_videos=5):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        videos = []
        for entry in root.findall("atom:entry", ns)[:max_videos]:
            video_id_el = entry.find("yt:videoId", ns)
            title_el = entry.find("atom:title", ns)
            published_el = entry.find("atom:published", ns)
            if video_id_el is None:
                continue
            video_id = video_id_el.text
            title = title_el.text if title_el is not None else ""
            published = published_el.text if published_el is not None else ""
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            videos.append(
                {
                    "video_id": video_id,
                    "title": title,
                    "published": published,
                    "url": video_url,
                }
            )
        return videos
    except Exception as e:
        print(f"[WARN] Failed to fetch channel {channel_id}: {e}", file=sys.stderr)
        return []


def main():
    channels = load_channels()
    processed = load_processed()

    new_videos = []
    for channel in channels:
        channel_id = channel["channel_id"]
        channel_name = channel["name"]
        print(
            f"[INFO] Checking {channel_name} ({channel_id})...", file=sys.stderr
        )
        videos = fetch_channel_videos(channel_id)
        for v in videos:
            if v["video_id"] not in processed:
                v["channel_name"] = channel_name
                new_videos.append(v)
                print(
                    f"[NEW]  {v['video_id']}: {v['title'][:60]}", file=sys.stderr
                )
            else:
                print(
                    f"[SKIP] {v['video_id']} (already processed)", file=sys.stderr
                )

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
