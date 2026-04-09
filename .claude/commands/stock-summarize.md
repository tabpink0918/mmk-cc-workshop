# stock-summarize: 영상 자막 취득 및 요약

특정 유튜브 영상의 자막을 가져와 한국 증시 관점으로 요약합니다.

## 입력

이 스킬은 다음 정보를 입력으로 받습니다:
- `VIDEO_URL`: 유튜브 영상 URL (예: https://www.youtube.com/watch?v=xxxxx)
- `VIDEO_TITLE`: 영상 제목
- `CHANNEL_NAME`: 채널명

## 실행 단계

1. `yt-dlp`로 한국어 자막을 가져옵니다 (mmk youtube transcript 대체):

```bash
yt-dlp --no-check-certificate --write-auto-subs --sub-lang ko --skip-download \
  --output "/tmp/transcript_%(id)s.%(ext)s" \
  "{VIDEO_URL}" 2>&1

# VTT 파일을 텍스트로 변환
python3 -c "
import re, glob
files = glob.glob('/tmp/transcript_*.ko.vtt')
if not files:
    print('자막 없음')
else:
    content = open(files[0]).read()
    lines = content.split('\n')
    result = []
    prev = None
    for line in lines:
        if '-->' in line or line.startswith('WEBVTT') or not line.strip(): continue
        clean = re.sub(r'<[^>]+>', '', line).strip()
        if clean and clean != prev:
            result.append(clean)
            prev = clean
    print('\n'.join(result))
"
```

2. 자막이 성공적으로 취득되면, 아래 형식으로 핵심 내용을 요약합니다:

### 요약 형식

**[채널명] 영상 제목**

📌 핵심 포인트:
- (포인트 1 — 증시 관련 수치/지수/종목 포함)
- (포인트 2)
- (포인트 3)
- (포인트 4, 있을 경우)
- (포인트 5, 있을 경우)

💡 투자 시사점: (1-2문장으로 오늘의 투자 관점 요약)

## 요약 지침

- 핵심 포인트는 3~5개로 제한
- 구체적인 수치(지수, 등락률, 목표주가 등)를 포함
- 언급된 주요 종목/ETF 명시
- 한국 투자자 관점에서 중요한 정보 우선
- 자막이 없거나 취득 실패 시: "자막 취득 실패: {오류 메시지}" 출력

## 출력

요약문을 텍스트로 반환합니다. 이 요약은 `/stock-notify` 스킬로 전달됩니다.
