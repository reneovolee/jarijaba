from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Path, Request
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


def _make_client() -> GraphClient:
    load_env()
    settings = load_settings()
    token = DeviceCodeTokenProvider(
        tenant_id=settings.tenant_id,
        client_id=settings.client_id,
        token_cache_path=settings.token_cache_path,
    ).acquire_token()
    return GraphClient(settings.graph_host, token["access_token"])


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


