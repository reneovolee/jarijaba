# Jarijaba - Teams 회식 장소 추천 앱

회식 장소 추천, 투표, 일정 등록을 위한 Microsoft Teams 앱입니다.

## 주요 기능

- 🤖 **AI 기반 회식 장소 추천**: LangGraph와 Azure OpenAI를 활용한 지능형 추천
- 🔍 **검색 API 연동**: 네이버 검색 API를 통한 실시간 맛집 검색
- 🗳️ **Teams 투표 기능**: 추천된 장소들에 대한 자동 투표 생성
- 📅 **Outlook 일정 등록**: Microsoft Graph API를 통한 일정 자동 등록

## 기술 스택

- **Backend**: FastAPI, Python 3.11+
- **AI/ML**: LangGraph, Azure OpenAI, LangChain
- **검색 API**: 네이버 검색 API (블로그, 뉴스, 웹)
- **Microsoft 통합**: Teams Bot Framework, Microsoft Graph API
- **패키지 관리**: uv

## 프로젝트 구조

```
jarijaba/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 메인 애플리케이션
│   ├── config.py            # 설정 관리
│   ├── models.py            # 데이터 모델
│   ├── agents/
│   │   ├── __init__.py
│   │   └── restaurant_agent.py  # LangGraph 기반 추천 에이전트
│   └── services/
│       ├── __init__.py
│       ├── naver_search_service.py # 네이버 검색 API 서비스
│       └── outlook_service.py   # Outlook 일정 서비스
├── pyproject.toml           # 프로젝트 설정 및 의존성
├── env.example             # 환경 변수 예시
├── run.py                  # 실행 스크립트
└── README.md
```

## 설치 및 실행

### 1. 의존성 설치

```bash
# uv 설치 (아직 설치되지 않은 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 프로젝트 의존성 설치
uv sync
```

### 2. 환경 변수 설정

```bash
# 환경 변수 파일 복사
cp env.example .env

# .env 파일을 편집하여 필요한 API 키들을 설정
```

필요한 환경 변수:
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API 키
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI 엔드포인트
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Azure OpenAI 배포명
# 네이버 검색 API는 무료 공개 API이므로 별도 키가 필요하지 않음
- `TEAMS_APP_ID`: Teams 앱 ID
- `TEAMS_APP_PASSWORD`: Teams 앱 비밀번호
- `MICROSOFT_GRAPH_CLIENT_ID`: Microsoft Graph 클라이언트 ID
- `MICROSOFT_GRAPH_CLIENT_SECRET`: Microsoft Graph 클라이언트 시크릿

### 3. 애플리케이션 실행

```bash
# 개발 모드로 실행
uv run python run.py

# 또는 직접 실행
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API 엔드포인트

### 1. Teams 메시지 처리
```
POST /api/messages
```
Teams에서 받은 메시지를 처리하고 회식 장소를 추천합니다.

### 2. 투표 생성
```
POST /api/polls
```
추천된 장소들에 대한 투표를 생성합니다.

### 3. 일정 등록
```
POST /api/events
```
선택된 장소로 Outlook 일정을 등록합니다.

### 4. 헬스 체크
```
GET /api/health
```
애플리케이션 상태를 확인합니다.

## 사용 방법

1. **Teams에서 봇과 대화**: "강남에서 회식 장소 추천해줘"와 같이 메시지를 보냅니다.

2. **AI 추천**: LangGraph 에이전트가 사용자의 요구사항을 분석하고 네이버 검색 API에서 적합한 맛집을 검색합니다.

3. **투표 생성**: 추천된 장소들에 대한 투표가 자동으로 생성됩니다.

4. **일정 등록**: 투표 결과에 따라 Outlook 일정이 자동으로 등록됩니다.

## LangGraph 에이전트 플로우

1. **쿼리 분류**: 사용자 메시지가 회식 장소 추천 요청인지 판단
2. **선호도 추출**: 지역, 예산, 음식 종류, 인원수 등 요구사항 추출
3. **맛집 검색**: 네이버 검색 API를 통한 실시간 맛집 검색 (블로그, 뉴스, 웹)
4. **추천 생성**: LLM을 통한 맞춤형 추천 및 설명 생성
5. **응답 포맷팅**: Teams 적응형 카드 형태로 최종 응답 생성

## 개발

### 코드 포맷팅
```bash
# Black으로 코드 포맷팅
uv run black app/

# isort로 import 정렬
uv run isort app/
```

### 타입 체크
```bash
# mypy로 타입 체크
uv run mypy app/
```

### 테스트
```bash
# pytest로 테스트 실행
uv run pytest
```

## 라이선스

MIT License

## 기여

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request