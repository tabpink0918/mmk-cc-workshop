# stock-monitor: 한국 증시 유튜브 모니터링 오케스트레이터

한국 증시 유튜브 채널을 모니터링하여 신규 영상을 자동으로 요약하고 Slack/Notion에 전달합니다.

## 모니터링 채널

- 한경글로벌마켓 — 키워드: 빈난새, 개장전요것만, 김현석, 월스트리트나우
- 한국경제TV — 키워드: 당잠사
- 증시각도기TV — 키워드: 증시각도기

## 실행 단계

### 1단계: 신규 영상 조회

아래 명령을 실행하여 신규 영상 목록을 가져옵니다:

```bash
cd /home/user/mmk-cc-workshop && python3 scripts/fetch_videos.py
```

JSON 결과를 파싱하여 `new_videos` 배열을 확인합니다.

**신규 영상이 없으면** 다음 메시지를 출력하고 종료합니다:
```
📭 신규 영상 없음 (2026-04-09 HH:MM KST)
다음 실행: 1시간 후
```

**신규 영상이 있으면** 2단계로 진행합니다.

### 2단계: 각 영상 처리

신규 영상 각각에 대해 순서대로 처리합니다:

#### 2a. 자막 취득 및 요약

```bash
mmk youtube transcript {VIDEO_URL}
```

자막 내용을 바탕으로 핵심 포인트 3~5개를 한국어로 요약합니다:
- 구체적인 수치(지수, 등락률, 목표주가) 포함
- 주요 종목/ETF/섹터 명시
- 한국 투자자 관점에서 중요한 정보 우선

#### 2b. Slack 알림 전송

`slack_send_message` MCP 도구를 사용하여 `#cc-workshop` (channel_id: `C0ARSJQ9U66`)에 전송:

```
📺 *[채널명]* 새 영상 요약

*제목:* {VIDEO_TITLE}
*게시일:* {날짜}
*링크:* {VIDEO_URL}

📌 핵심 포인트:
• (요약 bullet 1)
• (요약 bullet 2)
• (요약 bullet 3)
...

💡 투자 시사점: (1-2문장 요약)
```

#### 2c. Notion 저장

`notion-create-pages` MCP 도구를 사용하여 data_source_id `5358d760-8d92-4738-8f7f-2d98b9ba2e44`에 저장:

속성:
- `제목`: 영상 제목
- `채널`: 채널명
- `날짜`: 게시일 (YYYY-MM-DD 형식)
- `요약`: 요약 텍스트 (bullet points 포함)
- `URL`: 영상 URL
- `영상ID`: 영상 ID

#### 2d. 처리 완료 기록

아래 Python 코드를 실행하여 처리 완료 영상 ID를 저장합니다 (중복 방지):

```bash
python3 -c "
import json, datetime, os
path = '/home/user/mmk-cc-workshop/data/processed_videos.json'
with open(path) as f:
    data = json.load(f)
data['{VIDEO_ID}'] = {
    'title': '{VIDEO_TITLE}',
    'channel': '{CHANNEL_NAME}',
    'processed_at': datetime.datetime.now().isoformat()
}
with open(path, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('처리 완료 기록:', '{VIDEO_ID}')
"
```

### 3단계: 실행 결과 요약

모든 영상 처리 후 최종 보고:

```
====================================
📊 증시 모니터링 실행 결과
====================================
실행 시각: YYYY-MM-DD HH:MM KST
처리 영상: N개

1. [채널명] 영상 제목
   → Slack ✓ | Notion ✓

2. [채널명] 영상 제목
   → Slack ✓ | Notion ✓
====================================
다음 실행: 1시간 후
```

## 1시간 자동화 실행

Claude Code 세션에서 아래 명령으로 1시간마다 자동 실행합니다:

```
/loop 1h /stock-monitor
```

## 주의사항

- 자막이 없는 영상(Shorts, 라이브 등)은 자막 취득 실패로 처리하고 건너뜁니다
- 오류 발생 시 해당 영상을 건너뛰고 다음 영상으로 진행합니다
- 처리 완료된 영상은 `data/processed_videos.json`에 기록되어 재처리하지 않습니다
