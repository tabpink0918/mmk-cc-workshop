#!/usr/bin/env python3
"""Fetch new YouTube videos from Korean stock market channels via RSS."""

import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.error

DATA_DIR = Path(__file__).parent.parent / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"
PROCESSED_FILE = DATA_DIR / "processed.json"

NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'yt': 'http://www.youtube.com/xml/schemas/2015',
    'media': 'http://search.yahoo.com/mrss/',
}


def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def fetch_rss(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        print(f"[WARN] HTTP {e.code} for channel {channel_id}", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] Failed to fetch RSS for {channel_id}: {e}", file=sys.stderr)
    return None


def parse_entries(content, channel_name, since_hours=48):
    if not content:
        return []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"[WARN] XML parse error: {e}", file=sys.stderr)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    videos = []

    for entry in root.findall('atom:entry', NS):
        vid_id = entry.findtext('yt:videoId', namespaces=NS)
        title = entry.findtext('atom:title', namespaces=NS)
        published = entry.findtext('atom:published', namespaces=NS)
        link_el = entry.find('atom:link[@rel="alternate"]', NS)
        url = link_el.get('href') if link_el is not None else f"https://www.youtube.com/watch?v={vid_id}"

        if not vid_id:
            continue

        pub_dt = None
        if published:
            try:
                pub_dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
            except ValueError:
                pass

        if pub_dt and pub_dt < cutoff:
            continue

        videos.append({
            'video_id': vid_id,
            'title': title or '',
            'url': url,
            'published': published or '',
            'channel': channel_name,
        })

    return videos


def main():
    channels = load_json(CHANNELS_FILE, default=[])
    processed = load_json(PROCESSED_FILE, default={'processed': []})
    processed_ids = set(processed.get('processed', []))

    if not channels:
        print(f"[WARN] No channels configured in {CHANNELS_FILE}", file=sys.stderr)
        print(json.dumps([], ensure_ascii=False))
        return 0

    new_videos = []
    for ch in channels:
        channel_id = ch.get('channel_id', '').strip()
        channel_name = ch.get('name', channel_id)
        if not channel_id:
            continue

        print(f"[INFO] Checking: {channel_name} ({channel_id})", file=sys.stderr)
        content = fetch_rss(channel_id)
        entries = parse_entries(content, channel_name, since_hours=48)

        for v in entries:
            if v['video_id'] not in processed_ids:
                new_videos.append(v)
                print(f"[NEW] [{channel_name}] {v['title']} ({v['published']})", file=sys.stderr)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
