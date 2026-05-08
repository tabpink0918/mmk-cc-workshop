#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels.

Reads data/processed.json to skip already-processed videos.
Outputs JSON list of new videos to stdout.
"""

import json
import os
import sys
import xml.etree.ElementTree as ET

import requests

CHANNELS = {
    "삼프로TV": "UChlv4GSd7OQl3js-jkLOnFA",
    "슈카월드": "UCJo6G1u0e_-wS-JQn3T-zEw",
}

RSS_HEADERS = {"User-Agent": "curl/7.81.0"}

PROCESSED_FILE = os.path.join(os.path.dirname(__file__), "../data/processed.json")


def load_processed():
    try:
        with open(PROCESSED_FILE) as f:
            data = json.load(f)
            return set(data.get("processed", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def fetch_channel_videos(channel_name, channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=RSS_HEADERS, timeout=15)
            if r.status_code == 200:
                break
            print(f"[{channel_name}] RSS {r.status_code} (attempt {attempt+1})", file=sys.stderr)
        except Exception as e:
            print(f"[{channel_name}] attempt {attempt+1} error: {e}", file=sys.stderr)
    else:
        return []
    try:

        root = ET.fromstring(r.content)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        videos = []
        for entry in root.findall("atom:entry", ns):
            vid_id = entry.find("yt:videoId", ns).text
            title = entry.find("atom:title", ns).text
            published = entry.find("atom:published", ns).text[:10]
            videos.append(
                {
                    "id": vid_id,
                    "title": title,
                    "published": published,
                    "channel": channel_name,
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                }
            )
        return videos
    except Exception as e:
        print(f"[{channel_name}] Error fetching RSS: {e}", file=sys.stderr)
        return []


def main():
    processed = load_processed()
    all_videos = []

    for channel_name, channel_id in CHANNELS.items():
        videos = fetch_channel_videos(channel_name, channel_id)
        print(f"[{channel_name}] {len(videos)} videos fetched", file=sys.stderr)
        all_videos.extend(videos)

    new_videos = [v for v in all_videos if v["id"] not in processed]
    print(
        f"Total new: {len(new_videos)} (skipped {len(all_videos) - len(new_videos)} processed)",
        file=sys.stderr,
    )

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
