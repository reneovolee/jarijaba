from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.responses import RedirectResponse
import secrets
import base64
import os
from urllib.parse import urlencode
from pydantic import BaseModel, Field

try:
    from .env import load_env
    from .config import load_settings
    from .auth import DeviceCodeTokenProvider
    from .graph_client import GraphClient
    from .rsvp import verify_params
except ImportError:
    from env import load_env  # type: ignore
    from config import load_settings  # type: ignore
    from auth import DeviceCodeTokenProvider  # type: ignore
    from graph_client import GraphClient  # type: ignore
    from rsvp import verify_params  # type: ignore


# Ensure environment variables (.env) are loaded for all endpoints (including /rsvp)
load_env()


class ScheduleRequest(BaseModel):
    users: List[str]
    start: str
    end: str
    interval: int = 30
    timezone: str = "Asia/Seoul"


class CreateEventRequest(BaseModel):
    subject: str
    start: str
    end: str
    timezone: str = "Asia/Seoul"
    attendees: Optional[List[str]] = None
    body: Optional[str] = None
    location: Optional[str] = None


class UpdateEventRequest(BaseModel):
    location: Optional[str] = None
    bodyAppend: Optional[str] = Field(default=None, description="Appended HTML content")


class AutoScheduleRequest(BaseModel):
    users: List[str]
    start: str
    end: str
    duration: int = 60
    interval: int = 30
    timezone: str = "Asia/Seoul"
    subject: str = "회식"
    body: Optional[str] = None
    location: Optional[str] = None


class AutoScheduleWithTeamsRequest(BaseModel):
    users: List[str]
    start: str
    end: str
    duration: int = 60
    interval: int = 30
    timezone: str = "Asia/Seoul"
    subject: str = "회식"
    body: Optional[str] = None
    location: Optional[str] = None
    teams_chat_id: str  # Teams 채팅 ID


class ScheduleProposalRequest(BaseModel):
    users: List[str]
    start: str
    end: str
    duration: int = 60
    interval: int = 30
    timezone: str = "Asia/Seoul"
    subject: str = "회식"
    body: Optional[str] = None
    location: Optional[str] = None
    teams_chat_id: str  # Teams 채팅 ID


def _make_client() -> GraphClient:
    load_env()
    settings = load_settings()
    token = DeviceCodeTokenProvider(
        tenant_id=settings.tenant_id,
        client_id=settings.client_id,
        token_cache_path=settings.token_cache_path,
    ).acquire_token()
    return GraphClient(settings.graph_host, token["access_token"])


def _oauth_settings():
    tenant = os.getenv("AZURE_TENANT_ID", "common")
    client_id = os.getenv("AZURE_CLIENT_ID")
    redirect_uri = os.getenv("OAUTH_REDIRECT_URI")  # e.g., https://<domain>/oauth/callback
    client_secret = os.getenv("OAUTH_CLIENT_SECRET")  # optional, for confidential clients
    auth_endpoint = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
    token_endpoint = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    return tenant, client_id, redirect_uri, auth_endpoint, token_endpoint, client_secret


app = FastAPI(title="Schedule Manager API", version="1.0.0")


@app.post("/schedule/getSchedule")
def get_schedule(req: ScheduleRequest):
    client = _make_client()
    try:
        data = client.get_schedule(
            users=req.users,
            start=req.start,
            end=req.end,
            interval_minutes=req.interval,
            timezone=req.timezone,
        )
        return data
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/events")
def create_event(req: CreateEventRequest):
    client = _make_client()
    try:
        data = client.create_event(
            subject=req.subject,
            start=req.start,
            end=req.end,
            timezone=req.timezone,
            attendees=req.attendees,
            body=req.body,
            location=req.location,
        )
        return data
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/events/{event_id}")
def update_event(event_id: str = Path(...), req: UpdateEventRequest | None = None):
    client = _make_client()
    try:
        client.update_event(
            event_id=event_id,
            location=req.location if req else None,
            body_append=req.bodyAppend if req else None,
        )
        return {"status": "updated"}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/autoschedule")
def autoschedule(req: AutoScheduleRequest):
    client = _make_client()
    try:
        sched = client.get_schedule(req.users, req.start, req.end, req.interval, req.timezone)
        views = client.availability_to_slots(sched, req.interval)
        if not views:
            raise HTTPException(status_code=400, detail="no schedule data")

        length_needed = max(1, req.duration // req.interval + (1 if req.duration % req.interval else 0))
        slot_count = len(next(iter(views.values())))

        def is_free_at(i: int) -> bool:
            return all(views[u][i] == '0' for u in req.users)

        run = 0
        start_index: Optional[int] = None
        for i in range(slot_count):
            if is_free_at(i):
                if run == 0:
                    start_index = i
                run += 1
                if run >= length_needed:
                    break
            else:
                run = 0
                start_index = None
        if start_index is None or run < length_needed:
            raise HTTPException(status_code=404, detail="no common free slot")

        base = datetime.fromisoformat(req.start)
        slot_start = base + timedelta(minutes=start_index * req.interval)
        slot_end = slot_start + timedelta(minutes=req.duration)
        created = client.create_event(
            subject=req.subject,
            start=slot_start.strftime("%Y-%m-%dT%H:%M:%S"),
            end=slot_end.strftime("%Y-%m-%dT%H:%M:%S"),
            timezone=req.timezone,
            attendees=req.users,
            body=req.body,
            location=req.location,
        )
        return created
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/autoschedule_with_teams")
def autoschedule_with_teams(req: AutoScheduleWithTeamsRequest):
    """AI가 자동으로 최적 시간을 찾아 회의를 생성하고, Teams 채팅으로 RSVP 링크를 전송"""
    client = _make_client()
    try:
        # 1. 자동 스케줄링 (기존 로직)
        sched = client.get_schedule(req.users, req.start, req.end, req.interval, req.timezone)
        views = client.availability_to_slots(sched, req.interval)
        if not views:
            raise HTTPException(status_code=400, detail="no schedule data")

        length_needed = max(1, req.duration // req.interval + (1 if req.duration % req.interval else 0))
        slot_count = len(next(iter(views.values())))

        def is_free_at(i: int) -> bool:
            return all(views[u][i] == '0' for u in req.users)

        run = 0
        start_index: Optional[int] = None
        for i in range(slot_count):
            if is_free_at(i):
                if run == 0:
                    start_index = i
                run += 1
                if run >= length_needed:
                    break
            else:
                run = 0
                start_index = None
        if start_index is None or run < length_needed:
            raise HTTPException(status_code=404, detail="no common free slot")

        base = datetime.fromisoformat(req.start)
        slot_start = base + timedelta(minutes=start_index * req.interval)
        slot_end = slot_start + timedelta(minutes=req.duration)
        
        # 2. 회의 생성
        created = client.create_event(
            subject=req.subject,
            start=slot_start.strftime("%Y-%m-%dT%H:%M:%S"),
            end=slot_end.strftime("%Y-%m-%dT%H:%M:%S"),
            timezone=req.timezone,
            attendees=req.users,
            body=req.body,
            location=req.location,
        )
        
        # 3. Teams 채팅으로 RSVP 링크 전송
        ical_uid = created.get("iCalUId")
        if ical_uid:
            # 현재 ngrok URL 가져오기
            redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "https://6f3f0e121ad9.ngrok-free.app/oauth/callback")
            ngrok_base = redirect_uri.replace("/oauth/callback", "")
            
            rsvp_html = f"""
            <p>🤖 AI가 자동으로 스케줄한 회의: <strong>{req.subject}</strong></p>
            <p>📅 시간: {slot_start.strftime('%Y-%m-%d %H:%M')} - {slot_end.strftime('%H:%M')}</p>
            <p>👥 참석자: {', '.join(req.users)}</p>
            <p>참석 여부를 알려주세요:</p>
            <p>
                <a href='{ngrok_base}/rsvp_accept?icalUid={ical_uid}'>✅ 참석</a> | 
                <a href='{ngrok_base}/rsvp_accept?icalUid={ical_uid}&resp=no'>❌ 불참</a>
            </p>
            """
            
            # Teams 채팅으로 메시지 전송
            from .teams import send_teams_message
            teams_result = send_teams_message(req.teams_chat_id, rsvp_html)
            
            return {
                "event": created,
                "teams_message": teams_result,
                "rsvp_links": {
                    "accept": f"{ngrok_base}/rsvp_accept?icalUid={ical_uid}",
                    "decline": f"{ngrok_base}/rsvp_accept?icalUid={ical_uid}&resp=no"
                }
            }
        else:
            return {"event": created, "teams_message": "No iCalUId found"}
            
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


# 회의 제안을 저장할 임시 저장소
_proposal_store: dict[str, dict] = {}


@app.post("/schedule_proposal")
def schedule_proposal(req: ScheduleProposalRequest):
    """AI가 최적 시간을 찾고, Teams 채팅으로 회의 제안을 보냄 (회의 생성 전)"""
    client = _make_client()
    try:
        # 1. 자동 스케줄링 (기존 로직)
        sched = client.get_schedule(req.users, req.start, req.end, req.interval, req.timezone)
        views = client.availability_to_slots(sched, req.interval)
        if not views:
            raise HTTPException(status_code=400, detail="no schedule data")

        length_needed = max(1, req.duration // req.interval + (1 if req.duration % req.interval else 0))
        slot_count = len(next(iter(views.values())))

        def is_free_at(i: int) -> bool:
            return all(views[u][i] == '0' for u in req.users)

        run = 0
        start_index: Optional[int] = None
        for i in range(slot_count):
            if is_free_at(i):
                if run == 0:
                    start_index = i
                run += 1
                if run >= length_needed:
                    break
            else:
                run = 0
                start_index = None
        if start_index is None or run < length_needed:
            raise HTTPException(status_code=404, detail="no common free slot")

        base = datetime.fromisoformat(req.start)
        slot_start = base + timedelta(minutes=start_index * req.interval)
        slot_end = slot_start + timedelta(minutes=req.duration)
        
        # 2. 제안 ID 생성
        proposal_id = secrets.token_urlsafe(16)
        
        # 3. 제안 정보 저장
        _proposal_store[proposal_id] = {
            "users": req.users,
            "start": slot_start.strftime("%Y-%m-%dT%H:%M:%S"),
            "end": slot_end.strftime("%Y-%m-%dT%H:%M:%S"),
            "timezone": req.timezone,
            "subject": req.subject,
            "body": req.body,
            "location": req.location,
            "teams_chat_id": req.teams_chat_id
        }
        
        # 4. Teams 채팅으로 제안 메시지 전송
        # 현재 ngrok URL 가져오기
        redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "https://6f3f0e121ad9.ngrok-free.app/oauth/callback")
        ngrok_base = redirect_uri.replace("/oauth/callback", "")
        
        proposal_html = f"""
        <p>🤖 AI가 최적의 시간을 찾았습니다!</p>
        <p><strong>회의 제안:</strong> {req.subject}</p>
        <p>📅 시간: {slot_start.strftime('%Y-%m-%d %H:%M')} - {slot_end.strftime('%H:%M')}</p>
        <p>👥 참석자: {', '.join(req.users)}</p>
        <p>이 시간에 회의를 생성할까요?</p>
        <p>
            <a href='{ngrok_base}/create_meeting?proposal_id={proposal_id}'>✅ 회의 생성</a> | 
            <a href='{ngrok_base}/reject_proposal?proposal_id={proposal_id}'>❌ 거절</a>
        </p>
        """
        
        # Teams 채팅으로 메시지 전송
        from .teams import send_teams_message
        teams_result = send_teams_message(req.teams_chat_id, proposal_html)
        
        return {
            "proposal_id": proposal_id,
            "proposed_time": {
                "start": slot_start.strftime("%Y-%m-%dT%H:%M:%S"),
                "end": slot_end.strftime("%Y-%m-%dT%H:%M:%S")
            },
            "teams_message": teams_result,
            "action_links": {
                "create": f"{ngrok_base}/create_meeting?proposal_id={proposal_id}",
                "reject": f"{ngrok_base}/reject_proposal?proposal_id={proposal_id}"
            }
        }
            
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/create_meeting")
def create_meeting(proposal_id: str):
    """제안된 회의를 실제로 생성"""
    if proposal_id not in _proposal_store:
        raise HTTPException(status_code=404, detail="proposal not found")
    
    proposal = _proposal_store.pop(proposal_id)  # 한 번만 사용 가능하도록 제거
    
    client = _make_client()
    try:
        # 회의 생성
        created = client.create_event(
            subject=proposal["subject"],
            start=proposal["start"],
            end=proposal["end"],
            timezone=proposal["timezone"],
            attendees=proposal["users"],
            body=proposal["body"],
            location=proposal["location"],
        )
        
        # Teams 채팅으로 성공 메시지 전송
        success_html = f"""
        <p>✅ 회의가 성공적으로 생성되었습니다!</p>
        <p><strong>{proposal["subject"]}</strong></p>
        <p>📅 {proposal["start"]} - {proposal["end"]}</p>
        <p>👥 참석자: {', '.join(proposal["users"])}</p>
        """
        
        from .teams import send_teams_message
        teams_result = send_teams_message(proposal["teams_chat_id"], success_html)
        
        return {
            "status": "created",
            "event": created,
            "teams_message": teams_result
        }
        
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reject_proposal")
def reject_proposal(proposal_id: str):
    """제안된 회의를 거절"""
    if proposal_id not in _proposal_store:
        raise HTTPException(status_code=404, detail="proposal not found")
    
    proposal = _proposal_store.pop(proposal_id)
    
    # Teams 채팅으로 거절 메시지 전송
    reject_html = f"""
    <p>❌ 회의 제안이 거절되었습니다.</p>
    <p><strong>{proposal["subject"]}</strong></p>
    <p>📅 {proposal["start"]} - {proposal["end"]}</p>
    """
    
    from .teams import send_teams_message
    teams_result = send_teams_message(proposal["teams_chat_id"], reject_html)
    
    return {
        "status": "rejected",
        "teams_message": teams_result
    }


@app.get("/rsvp")
def rsvp(request: Request):
    # Query: optional eventId, optional user, resp, sig, and optionally subject/start/end/timezone/location/attendees
    q = dict(request.query_params)
    event_id = q.get("eventId")
    user = q.get("user")
    resp = q.get("resp")
    sig = q.get("sig")
    if not resp or not sig:
        raise HTTPException(status_code=400, detail="missing parameters")
    # reconstruct signed subset
    params = {k: v for k, v in q.items() if k != "sig"}
    if not verify_params(params, sig):
        raise HTTPException(status_code=401, detail="invalid signature")

    client = _make_client()
    try:
        if event_id:
            note = f"RSVP from {user or 'unknown'}: {'참석' if resp == 'yes' else '불참'}"
            client.update_event(event_id=event_id, body_append=note)
            return {"status": "ok", "message": note}
        # No event yet: create one on the fly when 'yes'
        if resp != "yes":
            return {"status": "ok", "message": "declined"}
        subject = q.get("subject", "회식")
        start = q.get("start")
        end = q.get("end")
        timezone = q.get("timezone", "Asia/Seoul")
        location = q.get("location")
        attendees = q.get("attendees")
        atts = [a.strip() for a in attendees.split(",") if a.strip()] if attendees else None
        created = client.create_event(
            subject=subject,
            start=start,
            end=end,
            timezone=timezone,
            attendees=atts,
            body=f"Auto-created from RSVP by {user or 'unknown'}",
            location=location,
            send_invitations=True,
        )
        return {"status": "created", "eventId": created.get("id"), "webLink": created.get("webLink")}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


# --- OAuth PKCE RSVP Accept ---
_pkce_store: dict[str, dict] = {}


@app.get("/rsvp_accept")
def rsvp_accept(icalUid: str, state: str | None = None):
    # Start OAuth PKCE flow
    tenant, client_id, redirect_uri, auth_endpoint, _, _ = _oauth_settings()
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=500, detail="OAuth not configured (AZURE_CLIENT_ID/OAUTH_REDIRECT_URI)")

    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    code_challenge = base64.urlsafe_b64encode(
        __import__("hashlib").sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")
    nonce = secrets.token_urlsafe(16)
    req_state = secrets.token_urlsafe(16)
    _pkce_store[req_state] = {"verifier": code_verifier, "ical": icalUid, "nonce": nonce}

    scopes = ["openid", "profile", "offline_access", "Calendars.ReadWrite"]
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": " ".join(scopes),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": req_state,
        "nonce": nonce,
    }
    return RedirectResponse(url=f"{auth_endpoint}?{urlencode(params)}")


@app.get("/oauth/callback")
def oauth_callback(code: str, state: str):
    # Exchange code for token and accept event
    tenant, client_id, redirect_uri, _, token_endpoint, client_secret = _oauth_settings()
    if state not in _pkce_store:
        raise HTTPException(status_code=400, detail="invalid state")
    entry = _pkce_store.pop(state)
    verifier = entry["verifier"]
    ical_uid = entry["ical"]

    data = {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }
    if client_secret:
        data["client_secret"] = client_secret
    import requests as _rq

    tok = _rq.post(token_endpoint, data=data, timeout=60)
    if not tok.ok:
        # Surface detailed error for debugging
        raise HTTPException(status_code=tok.status_code, detail=tok.text)
    access = tok.json().get("access_token")
    if not access:
        raise HTTPException(status_code=400, detail="no access token")

    client = GraphClient(load_settings().graph_host, access)
    target_id = client.find_event_by_icaluid(ical_uid)
    if not target_id:
        raise HTTPException(status_code=404, detail="event not found for attendee")
    
    try:
        client.accept_event(target_id, comment="Accepted via RSVP link", send_response=True)
        return {"status": "accepted", "eventId": target_id}
    except Exception as e:
        # If user is organizer, return success message instead of error
        if "meeting organizer" in str(e).lower():
            return {"status": "organizer", "message": "You are the meeting organizer. No response needed.", "eventId": target_id}
        else:
            raise HTTPException(status_code=500, detail=str(e))


