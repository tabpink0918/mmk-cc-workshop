#!/usr/bin/env python3
"""Summarize a YouTube video transcript using Claude API."""

import json
import sys
from pathlib import Path

import anthropic
import importlib.util

def _load_transcript_module():
    spec = importlib.util.spec_from_file_location(
        "get_transcript", Path(__file__).parent / "get-transcript.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_transcript_mod = _load_transcript_module()
get_transcript = _transcript_mod.get_transcript

SYSTEM_PROMPT = """당신은 한국 주식 투자 전문 애널리스트입니다.
유튜브 자막을 분석하여 투자자에게 유용한 한국어 요약을 작성합니다.

요약 형식:
## 📊 핵심 포인트 (3-5개)
- 각 포인트는 구체적인 수치나 사실 위주로 작성

## 📈 언급 종목/섹터
- 종목명 (티커): 언급 내용 요약

## 💡 투자 시사점
- 핵심 투자 시사점 1-2문장
"""


def summarize(video_id: str, title: str, channel: str) -> dict:
    """Get transcript and return AI summary."""
    print(f"  자막 추출 중: {video_id}...", file=sys.stderr)
    transcript = get_transcript(video_id)
    # Truncate to ~15k chars to stay within token limits
    if len(transcript) > 15000:
        transcript = transcript[:15000] + "..."

    print(f"  요약 중 (Claude)...", file=sys.stderr)
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"채널: {channel}\n제목: {title}\n\n자막:\n{transcript}",
            }
        ],
    )
    summary = message.content[0].text
    return {
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "summary": summary,
    }


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: summarize-video.py <video_id> <title> <channel>")
        sys.exit(1)
    video_id, title, channel = sys.argv[1], sys.argv[2], sys.argv[3]
    result = summarize(video_id, title, channel)
    print(json.dumps(result, ensure_ascii=False, indent=2))
