#!/usr/bin/env python3
"""
Fetches new videos from Korean stock market YouTube channels.
Compares against data/processed.json and outputs new video URLs.
"""

import json
import re
import sys
import os
import requests

CHANNELS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'channels.json')
PROCESSED_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed.json')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
}


def load_processed():
    try:
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def fetch_channel_videos(channel):
    """Scrape recent video IDs and titles from a YouTube channel page."""
    url = channel['url']
    try:
        r = requests.get(url, headers=HEADERS, timeout=20,
                        verify=os.environ.get('REQUESTS_CA_BUNDLE'))
        r.raise_for_status()
    except Exception as e:
        print(f"  ⚠️  Failed to fetch {channel['name']}: {e}", file=sys.stderr)
        return []

    # Extract video IDs preserving order (dedup with dict)
    video_ids = list(dict.fromkeys(
        re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
    ))

    videos = []
    for vid_id in video_ids[:10]:  # Check top 10 per channel
        # Try to get title from the page
        title_pattern = rf'"videoId":"{re.escape(vid_id)}".*?"title":\{{"runs":\[\{{"text":"([^"]+)"'
        title_match = re.search(title_pattern, r.text, re.DOTALL)

        if not title_match:
            # Fallback: search near videoId in context
            idx = r.text.find(f'"videoId":"{vid_id}"')
            if idx >= 0:
                context = r.text[idx:idx + 500]
                tm = re.search(r'"text":"([^"]{5,})"', context)
                title = tm.group(1) if tm else ''
            else:
                title = ''
        else:
            title = title_match.group(1)

        videos.append({
            'id': vid_id,
            'title': title,
            'url': f'https://www.youtube.com/watch?v={vid_id}',
            'channel': channel['name'],
            'channel_handle': channel['handle'],
        })

    return videos


def get_video_metadata(video_url):
    """Fetch title and basic metadata from individual video page."""
    try:
        r = requests.get(video_url, headers=HEADERS, timeout=20,
                        verify=os.environ.get('REQUESTS_CA_BUNDLE'))
        vd_idx = r.text.find('videoDetails')
        if vd_idx < 0:
            return {}
        section = r.text[vd_idx:vd_idx + 1000]
        title_m = re.search(r'"simpleText":"([^"]+)"', section)
        views_m = re.search(r'([\d,]+) views', section)
        time_m = re.search(r'(\d+ \w+ ago|[A-Za-z]+ \d+, \d{4})', section)
        return {
            'title': title_m.group(1) if title_m else '',
            'views': views_m.group(1) if views_m else '',
            'published': time_m.group(1) if time_m else '',
        }
    except Exception:
        return {}


def main():
    with open(CHANNELS_FILE) as f:
        channels = json.load(f)

    processed = load_processed()
    new_videos = []

    for channel in channels:
        print(f"Checking {channel['name']}...", file=sys.stderr)
        videos = fetch_channel_videos(channel)
        for v in videos:
            if v['id'] not in processed:
                # Enrich with individual page metadata
                meta = get_video_metadata(v['url'])
                if meta.get('title'):
                    v['title'] = meta['title']
                v['views'] = meta.get('views', '')
                v['published'] = meta.get('published', '')
                new_videos.append(v)
                print(f"  NEW: {v['id']} - {v['title'][:60]}", file=sys.stderr)

    # Output as JSON for the calling process
    print(json.dumps(new_videos, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
