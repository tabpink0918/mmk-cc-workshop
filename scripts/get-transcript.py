#!/usr/bin/env python3
"""Download and parse YouTube auto-generated captions into plain text."""

import re
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_vtt(vtt_text: str) -> str:
    """Convert VTT caption text to clean plain text."""
    lines = vtt_text.splitlines()
    seen = set()
    result = []
    for line in lines:
        # Skip header, timestamps, and blank lines
        if not line.strip() or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}", line):
            continue
        # Strip inline timing tags like <00:00:01.234><c>text</c>
        clean = re.sub(r"<[^>]+>", "", line).strip()
        clean = re.sub(r"&gt;", ">", clean)
        clean = re.sub(r"&lt;", "<", clean)
        clean = re.sub(r"&amp;", "&", clean)
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return " ".join(result)


def get_transcript(video_id: str, lang: str = "ko") -> str:
    """Download auto-generated subtitles and return clean text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = str(Path(tmpdir) / "sub")
        result = subprocess.run(
            [
                "yt-dlp",
                "--write-auto-sub",
                "--no-download",
                "--skip-download",
                "--sub-lang", lang,
                "--no-warnings",
                "--no-check-certificates",
                "--quiet",
                "-o", output_template,
                f"https://www.youtube.com/watch?v={video_id}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Find the generated VTT file
        vtt_files = list(Path(tmpdir).glob(f"*.{lang}.vtt"))
        if not vtt_files:
            # Try any VTT file
            vtt_files = list(Path(tmpdir).glob("*.vtt"))
        if not vtt_files:
            raise FileNotFoundError(f"No subtitle file generated for {video_id}. stderr: {result.stderr[:200]}")
        vtt_text = vtt_files[0].read_text(encoding="utf-8")
        return parse_vtt(vtt_text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: get-transcript.py <video_id> [lang]")
        sys.exit(1)
    video_id = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "ko"
    try:
        text = get_transcript(video_id, lang)
        print(text)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
