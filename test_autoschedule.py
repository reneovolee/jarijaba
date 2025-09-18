import requests
import json

# 새로운 API 테스트: 회의 제안 (회의 생성 전 승인)
response = requests.post('http://localhost:8000/schedule_proposal', json={
    'users': [
        'year_book@lgprompthon.dev',
        'hcns@lgprompthon.dev', 
        'eunhoolee@lgprompthon.dev'
    ],
    'start': '2025-09-19T18:00:00',
    'end': '2025-09-19T20:00:00',
    'duration': 60,
    'interval': 30,
    'timezone': 'Asia/Seoul',
    'subject': '회식',
    'body': 'AI가 자동으로 스케줄한 회식입니다',
    'teams_chat_id': '19:349f960616634e3fadae415e37ba0736@thread.v2'  # Teams 채팅 ID
})

print(f'Status Code: {response.status_code}')
print(f'Response: {response.json()}')

# 응답에서 proposal_id를 가져와서 회의 생성 테스트
if response.status_code == 200:
    data = response.json()
    proposal_id = data.get('proposal_id')
    if proposal_id:
        print(f'\n제안 ID: {proposal_id}')
        print(f'회의 생성 링크: {data.get("action_links", {}).get("create")}')
        print(f'제안 거절 링크: {data.get("action_links", {}).get("reject")}')
