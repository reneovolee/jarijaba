from __future__ import annotations

import json
from typing import Dict, List, Optional

import requests


def post_adaptive_card(webhook_url: str, card: Dict) -> None:
    headers = {"Content-Type": "application/json"}
    payload = {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": card}]}
    resp = requests.post(webhook_url, headers=headers, data=json.dumps(payload), timeout=30)
    resp.raise_for_status()


def build_event_card(
    subject: str,
    start: str,
    end: str,
    timezone: str,
    location: Optional[str],
    attendees: Optional[List[str]],
    web_link: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict:
    facts: List[Dict[str, str]] = [
        {"title": "시작", "value": f"{start} ({timezone})"},
        {"title": "종료", "value": f"{end} ({timezone})"},
    ]
    if location:
        facts.append({"title": "장소", "value": location})
    if attendees:
        facts.append({"title": "참석자", "value": ", ".join(attendees)})
    if note:
        facts.append({"title": "비고", "value": note})

    actions: List[Dict] = []
    if web_link:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "Outlook에서 열기",
            "url": web_link,
        })

    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": subject, "weight": "Bolder", "size": "Medium"},
            {"type": "FactSet", "facts": facts},
        ],
        "actions": actions,
    }


