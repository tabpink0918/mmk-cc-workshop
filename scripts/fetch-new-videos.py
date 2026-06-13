#!/usr/bin/env python3
"""
Fetch new videos from Korean stock market YouTube channels.
Uses YouTube RSS feeds (no API key required).
Outputs new video list as JSON to stdout.
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS_FILE = os.path.join(BASE_DIR, 'data', 'channels.json')
PROCESSED_FILE = os.path.join(BASE_DIR, 'data', 'processed.json')

RSS_URL = 'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'yt': 'http://www.youtube.com/xml/schemas/2015',
    'media': 'http://search.yahoo.com/mrss/',
}


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def fetch_rss(channel_id):
    url = RSS_URL.format(channel_id=channel_id)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as e:
        print(f'  [warn] RSS fetch failed: {e}', file=sys.stderr)
        return None


def parse_entries(xml_data, channel_name, max_entries=3):
    root = ET.fromstring(xml_data)
    videos = []
    for entry in root.findall('atom:entry', NS)[:max_entries]:
        video_id = entry.findtext('yt:videoId', '', NS)
        title = entry.findtext('atom:title', '', NS)
        published = entry.findtext('atom:published', '', NS)
        if video_id:
            videos.append({
                'video_id': video_id,
                'title': title,
                'url': f'https://www.youtube.com/watch?v={video_id}',
                'channel': channel_name,
                'published': published,
            })
    return videos


def main():
    channels_data = load_json(CHANNELS_FILE, {'channels': []})
    processed_data = load_json(PROCESSED_FILE, {'processed_ids': []})
    processed_ids = set(processed_data.get('processed_ids', []))

    channels = channels_data.get('channels', [])
    if not channels:
        print('No channels configured in data/channels.json', file=sys.stderr)
        sys.exit(1)

    new_videos = []

    for ch in channels:
        channel_id = ch['id']
        channel_name = ch['name']
        print(f'Checking: {channel_name} ({channel_id})', file=sys.stderr)

        xml_data = fetch_rss(channel_id)
        if not xml_data:
            continue

        try:
            videos = parse_entries(xml_data, channel_name)
        except ET.ParseError as e:
            print(f'  [warn] XML parse error: {e}', file=sys.stderr)
            continue

        for v in videos:
            if v['video_id'] not in processed_ids:
                new_videos.append(v)
                print(f'  NEW: [{v["published"][:10]}] {v["title"]}', file=sys.stderr)
            else:
                print(f'  SKIP: {v["title"]}', file=sys.stderr)

    print(f'\nTotal new videos: {len(new_videos)}', file=sys.stderr)
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))
    return new_videos


if __name__ == '__main__':
    main()
