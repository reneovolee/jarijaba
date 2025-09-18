from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, StateGraph

try:
    from .auth import DeviceCodeTokenProvider
    from .config import load_settings
    from .graph_client import GraphClient
    from .env import load_env
except ImportError:
    # Allow running as a script context
    from auth import DeviceCodeTokenProvider  # type: ignore
    from config import load_settings  # type: ignore
    from graph_client import GraphClient  # type: ignore
    from env import load_env  # type: ignore


def _make_client() -> GraphClient:
    load_env()
    settings = load_settings()
    token = DeviceCodeTokenProvider(
        tenant_id=settings.tenant_id,
        client_id=settings.client_id,
        token_cache_path=settings.token_cache_path,
    ).acquire_token()
    return GraphClient(settings.graph_host, token["access_token"])


def build_agent():
    sg = StateGraph(dict)

    def route(state: Dict[str, Any]) -> Dict[str, Any]:
        # Identity node; routing is defined via conditional edges
        return state

    def run_schedule(state: Dict[str, Any]) -> Dict[str, Any]:
        client = _make_client()
        params = state.get("params", {})
        data = client.get_schedule(
            users=params.get("users", []),
            start=params.get("start"),
            end=params.get("end"),
            interval_minutes=int(params.get("interval", 30)),
            timezone=params.get("timezone", "Asia/Seoul"),
        )
        return {**state, "result": data}

    def run_create(state: Dict[str, Any]) -> Dict[str, Any]:
        client = _make_client()
        params = state.get("params", {})
        data = client.create_event(
            subject=params["subject"],
            start=params["start"],
            end=params["end"],
            timezone=params.get("timezone", "Asia/Seoul"),
            attendees=params.get("attendees"),
            body=params.get("body"),
            location=params.get("location"),
        )
        return {**state, "result": data}

    def run_update(state: Dict[str, Any]) -> Dict[str, Any]:
        client = _make_client()
        params = state.get("params", {})
        client.update_event(
            event_id=params["id"],
            location=params.get("location"),
            body_append=params.get("bodyAppend"),
        )
        return {**state, "result": {"status": "updated"}}

    def run_autoschedule(state: Dict[str, Any]) -> Dict[str, Any]:
        client = _make_client()
        p = state.get("params", {})
        users = p["users"]
        start = p["start"]
        end = p["end"]
        duration = int(p.get("duration", 60))
        interval = int(p.get("interval", 30))
        tz = p.get("timezone", "Asia/Seoul")

        sched = client.get_schedule(users, start, end, interval, tz)
        views = client.availability_to_slots(sched, interval)
        # Compute first common contiguous free block of required length
        # availabilityView: 0=free, 1=tentative, 2=busy, 3=OOF, 4=workingElsewhere, 5=unknown
        # We treat only '0' as free
        if not views:
            return {**state, "result": {"error": "no schedule data"}}
        # Defensive: ensure each requested user has availabilityView and align lengths
        available_users = [u for u in users if u in views and len(views[u]) > 0]
        if len(available_users) != len(users):
            missing = [u for u in users if u not in views or len(views[u]) == 0]
            return {**state, "result": {"error": "missing schedule for users", "users": missing}}
        length_needed = max(1, duration // interval + (1 if duration % interval else 0))
        slot_count = min(len(views[u]) for u in available_users)
        if slot_count == 0:
            return {**state, "result": {"error": "no schedule slots"}}
        def is_free_at(i: int) -> bool:
            return all(i < len(views[u]) and views[u][i] == '0' for u in available_users)
        run = 0
        start_index = None
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
            return {**state, "result": {"error": "no common free slot"}}

        # compute start/end ISO by adding indices to start
        # We rely on client side to pass ISO strings; we compute via pandas-free approach
        from datetime import datetime, timedelta
        base = datetime.fromisoformat(start)
        slot_start = base + timedelta(minutes=start_index * interval)
        slot_end = slot_start + timedelta(minutes=duration)
        created = client.create_event(
            subject=p.get("subject", "회식"),
            start=slot_start.strftime("%Y-%m-%dT%H:%M:%S"),
            end=slot_end.strftime("%Y-%m-%dT%H:%M:%S"),
            timezone=tz,
            attendees=users,
            body=p.get("body"),
            location=p.get("location"),
            send_invitations=True,
        )
        return {**state, "result": created}

    sg.add_node("schedule", run_schedule)
    sg.add_node("create", run_create)
    sg.add_node("update", run_update)
    sg.add_node("autoschedule", run_autoschedule)

    # Router entry
    sg.add_node("route", route)
    sg.set_entry_point("route")
    sg.add_conditional_edges(
        "route",
        lambda s: s.get("intent", "schedule"),
        {
            "schedule": "schedule",
            "create": "create",
            "update": "update",
            "autoschedule": "autoschedule",
        },
    )
    sg.add_edge("schedule", END)
    sg.add_edge("create", END)
    sg.add_edge("update", END)
    sg.add_edge("autoschedule", END)

    return sg.compile()


