from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

# Allow running as a script: python jarijaba/schedule-manager/src/cli.py
if __package__ is None or __package__ == "":
    this_dir = Path(__file__).resolve().parent
    sys.path.append(str(this_dir))
    from agent import build_agent  # type: ignore
    from auth import DeviceCodeTokenProvider  # type: ignore
    from config import load_settings  # type: ignore
    from graph_client import GraphClient  # type: ignore
    from env import load_env  # type: ignore
    from rsvp import build_rsvp_url  # type: ignore
else:
    from .agent import build_agent
    from .auth import DeviceCodeTokenProvider
    from .config import load_settings
    from .graph_client import GraphClient
    from .env import load_env
    from .rsvp import build_rsvp_url


def _get_client() -> GraphClient:
    load_env()
    settings = load_settings()
    token = DeviceCodeTokenProvider(
        tenant_id=settings.tenant_id,
        client_id=settings.client_id,
        token_cache_path=settings.token_cache_path,
    ).acquire_token()
    return GraphClient(settings.graph_host, token["access_token"])


def cmd_schedule(args: argparse.Namespace) -> None:
    client = _get_client()
    users: List[str] = [u.strip() for u in args.users.split(",") if u.strip()]
    data = client.get_schedule(users, args.start, args.end, args.interval, args.timezone)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_create(args: argparse.Namespace) -> None:
    client = _get_client()
    attendees = [a.strip() for a in (args.attendees or "").split(",") if a.strip()]
    data = client.create_event(
        subject=args.subject,
        start=args.start,
        end=args.end,
        timezone=args.timezone,
        attendees=attendees or None,
        body=args.body,
        location=args.location,
        send_invitations=True,
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_update(args: argparse.Namespace) -> None:
    client = _get_client()
    client.update_event(
        event_id=args.id,
        location=args.location,
        body_append=args.bodyAppend,
    )
    print(json.dumps({"status": "updated"}, ensure_ascii=False))


def cmd_agent(args: argparse.Namespace) -> None:
    agent = build_agent()
    params = json.loads(args.params) if args.params else {}
    state = {"intent": args.intent, "params": params}
    result = agent.invoke(state)
    print(json.dumps(result.get("result"), ensure_ascii=False, indent=2))


def cmd_autoschedule(args: argparse.Namespace) -> None:
    # Use agent implementation to avoid duplicating logic
    agent = build_agent()
    params = {
        "users": [u.strip() for u in args.users.split(",") if u.strip()],
        "start": args.start,
        "end": args.end,
        "duration": args.duration,
        "interval": args.interval,
        "timezone": args.timezone,
        "subject": args.subject,
        "body": args.body,
        "location": args.location,
    }
    result = agent.invoke({"intent": "autoschedule", "params": params})
    out = result.get("result")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.webhook and isinstance(out, dict) and out.get("id"):
        try:
            from .teams import post_adaptive_card, build_event_card
        except ImportError:
            from teams import post_adaptive_card, build_event_card  # type: ignore
        attendees = [a.get("emailAddress",{}).get("address") for a in (out.get("attendees") or [])]
        card = build_event_card(
            subject=out.get("subject","회식"),
            start=out.get("start",{}).get("dateTime",""),
            end=out.get("end",{}).get("dateTime",""),
            timezone=out.get("start",{}).get("timeZone","Asia/Seoul"),
            location=(out.get("location") or {}).get("displayName"),
            attendees=attendees,
            web_link=out.get("webLink"),
            note=None,
        )
        post_adaptive_card(args.webhook, card)
    if args.flow and isinstance(out, dict):
        try:
            from .workflow import trigger_flow
        except ImportError:
            from workflow import trigger_flow  # type: ignore
        flow_payload = {
            "subject": out.get("subject"),
            "start": out.get("start",{}).get("dateTime"),
            "end": out.get("end",{}).get("dateTime"),
            "timezone": out.get("start",{}).get("timeZone"),
            "location": (out.get("location") or {}).get("displayName"),
            "attendees": [a.get("emailAddress",{}).get("address") for a in (out.get("attendees") or [])],
            "webLink": out.get("webLink"),
            "organizer": (out.get("organizer") or {}).get("emailAddress",{}).get("address"),
            "id": out.get("id"),
        }
        trigger_flow(args.flow, flow_payload)


def cmd_forward(args: argparse.Namespace) -> None:
    client = _get_client()
    recipients = [r.strip() for r in args.recipients.split(",") if r.strip()]
    client.forward_event(event_id=args.id, recipients=recipients, comment=args.comment)
    print(json.dumps({"status": "forwarded"}, ensure_ascii=False))


def cmd_sendmail(args: argparse.Namespace) -> None:
    client = _get_client()
    to = [r.strip() for r in args.to.split(",") if r.strip()]
    client.send_mail(to=to, subject=args.subject, body_html=args.body)
    print(json.dumps({"status": "sent"}, ensure_ascii=False))


def cmd_teams(args: argparse.Namespace) -> None:
    client = _get_client()
    if args.team and args.channel:
        res = client.send_channel_message(team_id=args.team, channel_id=args.channel, html_content=args.html)
    elif args.chat:
        res = client.send_chat_message(chat_id=args.chat, html_content=args.html)
    else:
        raise SystemExit("Provide either --team and --channel, or --chat")
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_send_rsvp(args: argparse.Namespace) -> None:
    client = _get_client()
    # Support two modes: with existing eventId OR with time window to create on accept
    if args.eventId:
        yes = build_rsvp_url(args.base_url, args.eventId, args.user, "yes")
        no = build_rsvp_url(args.base_url, args.eventId, args.user, "no")
    else:
        yes = build_rsvp_url(
            args.base_url,
            None,
            args.user,
            "yes",
            subject=args.subject,
            start=args.start,
            end=args.end,
            timezone=args.timezone,
            location=args.location,
            attendees=args.attendees or "",
        )
        no = build_rsvp_url(args.base_url, None, args.user, "no")
    html = f"<p>{args.subject}</p><p><a href='{yes}'>참석</a> | <a href='{no}'>불참</a></p>"
    if args.team and args.channel:
        res = client.send_channel_message(team_id=args.team, channel_id=args.channel, html_content=html)
    elif args.chat:
        res = client.send_chat_message(chat_id=args.chat, html_content=html)
    else:
        raise SystemExit("Provide either --team and --channel, or --chat")
    print(json.dumps(res, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("schedule-manager")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("schedule", help="Query free/busy schedule")
    sp.add_argument("--users", required=True, help="Comma separated user emails/UPNs")
    sp.add_argument("--start", required=True, help="ISO start, e.g. 2025-09-18T09:00:00")
    sp.add_argument("--end", required=True, help="ISO end, e.g. 2025-09-18T18:00:00")
    sp.add_argument("--interval", type=int, default=30)
    sp.add_argument("--timezone", default="Asia/Seoul")
    sp.set_defaults(func=cmd_schedule)

    cp = sub.add_parser("create", help="Create an event")
    cp.add_argument("--subject", required=True)
    cp.add_argument("--start", required=True)
    cp.add_argument("--end", required=True)
    cp.add_argument("--timezone", default="Asia/Seoul")
    cp.add_argument("--attendees", help="Comma separated emails")
    cp.add_argument("--body")
    cp.add_argument("--location")
    cp.set_defaults(func=cmd_create)

    up = sub.add_parser("update", help="Update an event")
    up.add_argument("--id", required=True)
    up.add_argument("--location")
    up.add_argument("--bodyAppend")
    up.set_defaults(func=cmd_update)

    ap = sub.add_parser("agent", help="Run intent-based agent")
    ap.add_argument("--intent", choices=["schedule", "create", "update"], required=True)
    ap.add_argument("--params", help="JSON parameters for the intent")
    ap.set_defaults(func=cmd_agent)

    asp = sub.add_parser("autoschedule", help="Find first common free slot and create event")
    asp.add_argument("--users", required=True, help="Comma separated user emails/UPNs")
    asp.add_argument("--start", required=True)
    asp.add_argument("--end", required=True)
    asp.add_argument("--duration", type=int, default=60, help="Desired duration in minutes")
    asp.add_argument("--interval", type=int, default=30)
    asp.add_argument("--timezone", default="Asia/Seoul")
    asp.add_argument("--subject", default="회식")
    asp.add_argument("--body")
    asp.add_argument("--location")
    asp.add_argument("--webhook", help="Teams Incoming Webhook URL to post result card")
    asp.add_argument("--flow", help="Power Automate HTTP trigger URL to invoke")
    asp.set_defaults(func=cmd_autoschedule)

    fp = sub.add_parser("forward", help="Forward an event to recipients")
    fp.add_argument("--id", required=True, help="Event ID")
    fp.add_argument("--recipients", required=True, help="Comma separated emails")
    fp.add_argument("--comment")
    fp.set_defaults(func=cmd_forward)

    sm = sub.add_parser("sendmail", help="Send a custom email via Graph")
    sm.add_argument("--to", required=True, help="Comma separated emails")
    sm.add_argument("--subject", required=True)
    sm.add_argument("--body", required=True)
    sm.set_defaults(func=cmd_sendmail)

    tm = sub.add_parser("teams", help="Send a Teams message via Microsoft Graph")
    tm.add_argument("--team", help="Team ID")
    tm.add_argument("--channel", help="Channel ID")
    tm.add_argument("--chat", help="Chat ID (use this OR team/channel)")
    tm.add_argument("--html", required=True, help="HTML content")
    tm.set_defaults(func=cmd_teams)

    rv = sub.add_parser("rsvp", help="Send RSVP links message to Teams")
    rv.add_argument("--base_url", required=True, help="Base URL where FastAPI is served (e.g. https://your-domain)")
    rv.add_argument("--eventId")
    rv.add_argument("--start", help="When no eventId: ISO start")
    rv.add_argument("--end", help="When no eventId: ISO end")
    rv.add_argument("--timezone", default="Asia/Seoul")
    rv.add_argument("--attendees", help="CSV attendees when creating on accept")
    rv.add_argument("--location")
    rv.add_argument("--user", required=True, help="Recipient identifier (email or name)")
    rv.add_argument("--subject", default="회식 참석 여부 확인")
    rv.add_argument("--team")
    rv.add_argument("--channel")
    rv.add_argument("--chat")
    rv.set_defaults(func=cmd_send_rsvp)

    return p


def main() -> None:
    load_env()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


