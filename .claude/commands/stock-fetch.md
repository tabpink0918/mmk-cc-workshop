# stock-fetch: 신규 증시 영상 조회

한국 증시 유튜브 채널에서 키워드에 맞는 신규 영상을 조회합니다.

## 실행 단계

1. 아래 명령을 실행하여 신규 영상 목록을 가져옵니다:

```bash
cd /home/user/mmk-cc-workshop && python3 scripts/fetch_videos.py
```

2. 결과 JSON을 파싱하여 다음을 보고합니다:
   - `count`: 신규 영상 수
   - `new_videos`: 각 영상의 제목, 채널, URL, 게시일
   - `errors`: 조회 실패한 채널 (있을 경우)

3. 신규 영상이 없으면 "신규 영상 없음" 메시지를 출력하고 종료합니다.

4. 신규 영상이 있으면 목록을 표 형태로 출력합니다:

| # | 제목 | 채널 | 게시일 |
|---|------|------|--------|
| 1 | ...  | ...  | ...    |

## 출력 형식

결과는 다음 JSON 구조로 반환됩니다 (다른 스킬에서 활용):

```json
{
  "new_videos": [
    {
      "video_id": "...",
      "title": "...",
      "url": "https://www.youtube.com/watch?v=...",
      "channel": "...",
      "published": "..."
    }
  ],
  "count": 0,
  "errors": []
}
```
