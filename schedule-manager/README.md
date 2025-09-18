## Schedule Manager (Microsoft Graph + LangGraph)

This project provides an agent that can:

- Query team free/busy using Microsoft Graph `GET /me/calendar/getSchedule`
- Create a confirmed dinner/drinks event using `POST /me/events`
- Update an existing event's location/reservation using `PATCH /me/events/{id}`

It uses:

- MSAL (Device Code) for OAuth2 (Azure AD)
- Microsoft Graph REST API
- LangGraph to orchestrate tool calls as an agent

### Prerequisites

- Python 3.10+
- An Azure AD App Registration with delegated permissions:
  - Calendars.ReadWrite
  - User.Read
  - offline_access

Have these values ready:

- Application (client) ID: `da1c90d2-e826-43b6-b2d5-836f9f2898c7`
- Directory (tenant) ID: Your tenant ID (or `common` for multi-tenant)

### Setup

1) Create a `.env` from the example and fill values

```bash
cp .env.example .env
# Edit .env accordingly
```

2) Create and activate a virtual environment, then install dependencies

```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1  # PowerShell on Windows
pip install -r requirements.txt
```

3) Login via device code on first run (the CLI triggers it)

### Usage (CLI)

```bash
# 1) Check free/busy schedules for users (comma-separated emails or UPNs)
python -m src.cli schedule \
  --users "alice@contoso.com,bob@contoso.com" \
  --start "2025-09-18T09:00:00" \
  --end "2025-09-18T18:00:00" \
  --interval 30

# 2) Create an event
python -m src.cli create \
  --subject "회식" \
  --start "2025-09-19T19:00:00" \
  --end "2025-09-19T21:00:00" \
  --timezone "Asia/Seoul" \
  --attendees "alice@contoso.com,bob@contoso.com" \
  --body "즐거운 회식입니다"

# 3) Update an event's location/reservation info
python -m src.cli update \
  --id "EVENT_ID_FROM_CREATE" \
  --location "강남 맛집" \
  --bodyAppend "예약: 02-123-4567 / 4명"
```

The agent variant lets you pass an intent and parameters as JSON; it will route to the right tool using LangGraph.

```bash
# Intent-based agent (schedule|create|update)
python -m src.cli agent \
  --intent schedule \
  --params '{"users": ["alice@contoso.com"], "start": "2025-09-18T09:00:00", "end": "2025-09-18T18:00:00", "interval": 30}'
```

### Run API (FastAPI + Swagger)

```bash
pip install -r requirements.txt
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: `http://localhost:8000/docs`
- Endpoints:
  - POST `/schedule/getSchedule`
  - POST `/events`
  - PATCH `/events/{event_id}`
  - POST `/autoschedule`

### Notes

- Token cache is stored locally at `.token_cache.bin` for convenience.
- Times should be ISO 8601. Provide `--timezone` when creating events.
- The code keeps dependencies minimal; you can wire an LLM into the agent later if needed.


