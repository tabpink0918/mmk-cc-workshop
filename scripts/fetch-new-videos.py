#!/usr/bin/env python3
"""Fetch new videos from Korean stock market YouTube channels via RSS."""

import json
import os
import sys
import xml.etree.ElementTree as ET
import urllib.request
from datetime import datetime, timedelta, timezone

CHANNELS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'channels.json')
PROCESSED_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed.json')
MAX_AGE_DAYS = 3

NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'yt': 'http://www.youtube.com/xml/schemas/2015',
}


def load_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def fetch_rss(channel_id):
    url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read()
    except Exception as e:
        print(f'Warning: RSS fetch failed for {channel_id}: {e}', file=sys.stderr)
        return None


def parse_entries(content, cutoff):
    root = ET.fromstring(content)
    videos = []
    for entry in root.findall('atom:entry', NS):
        video_id_el = entry.find('yt:videoId', NS)
        title_el = entry.find('atom:title', NS)
        published_el = entry.find('atom:published', NS)
        if None in (video_id_el, title_el, published_el):
            continue
        pub_dt = datetime.fromisoformat(published_el.text.replace('Z', '+00:00'))
        if pub_dt < cutoff:
            continue
        videos.append({
            'video_id': video_id_el.text,
            'title': title_el.text,
            'url': f'https://www.youtube.com/watch?v={video_id_el.text}',
            'published': published_el.text,
        })
    return videos


def main():
    channels_data = load_json(CHANNELS_FILE)
    processed_data = load_json(PROCESSED_FILE)
    processed_ids = set(processed_data.get('processed_ids', []))

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    new_videos = []

    for ch in channels_data.get('channels', []):
        channel_id = ch.get('channel_id', '')
        channel_name = ch.get('name', channel_id)
        content = fetch_rss(channel_id)
        if content is None:
            continue
        for video in parse_entries(content, cutoff):
            if video['video_id'] not in processed_ids:
                video['channel'] = channel_name
                new_videos.append(video)

    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
