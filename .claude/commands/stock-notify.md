# stock-notify: Slack 알림 + Notion 저장

영상 요약을 Slack에 전송하고 Notion 데이터베이스에 저장합니다.

## 입력

- `VIDEO_ID`: 유튜브 영상 ID
- `VIDEO_TITLE`: 영상 제목
- `VIDEO_URL`: 영상 URL
- `CHANNEL_NAME`: 채널명
- `PUBLISHED`: 게시일 (ISO 8601)
- `SUMMARY`: 요약 텍스트 (stock-summarize 결과)

## 실행 단계

### 1. Slack 알림 전송

아래 형식으로 Slack `#cc-workshop` 채널(ID: `C0ARSJQ9U66`)에 메시지를 보냅니다:

```
📺 *[채널명]* 새 영상 요약

*제목:* 영상 제목
*게시일:* YYYY-MM-DD
*링크:* https://www.youtube.com/watch?v=VIDEO_ID

---
📌 핵심 포인트:
• 포인트 1
• 포인트 2
• 포인트 3
...

💡 투자 시사점: ...
```

Slack MCP 도구(`slack_send_message`)를 사용하여 위 메시지를 channel_id `C0ARSJQ9U66`으로 전송합니다.

### 2. Notion 데이터베이스에 저장

Notion 데이터베이스(data_source_id: `5358d760-8d92-4738-8f7f-2d98b9ba2e44`)에 새 페이지를 생성합니다.

MCP 도구(`notion-create-pages`)를 사용하여 다음 속성으로 저장합니다:
- `제목`: 영상 제목
- `채널`: 채널명
- `date:날짜:start`: 게시일 (ISO 8601 date 형식, 예: "2026-04-09")
- `요약`: 요약 텍스트 (bullet points 포함)
- `URL`: 영상 URL
- `영상ID`: 영상 ID (중복 방지용)

### 3. 완료 보고

처리 완료 후 다음을 출력합니다:
```
✅ 알림 전송 완료: [영상 제목]
  - Slack: #cc-workshop ✓
  - Notion: 한국 증시 유튜브 요약 DB ✓
```
