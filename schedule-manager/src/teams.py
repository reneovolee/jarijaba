from __future__ import annotations

import json
from typing import Dict, List, Optional

import requests

try:
    from .env import load_env
    from .config import load_settings
    from .auth import DeviceCodeTokenProvider
    from .graph_client import GraphClient
except ImportError:
    from env import load_env  # type: ignore
    from config import load_settings  # type: ignore
    from auth import DeviceCodeTokenProvider  # type: ignore
    from graph_client import GraphClient  # type: ignore


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


def send_teams_message(chat_id: str, html_content: str) -> Dict:
    """Teams 채팅에 HTML 메시지를 전송"""
    load_env()
    settings = load_settings()
    
    # Graph API 클라이언트 생성
    token_provider = DeviceCodeTokenProvider(
        tenant_id=settings.tenant_id,
        client_id=settings.client_id,
        token_cache_path=settings.token_cache_path,
    )
    token = token_provider.acquire_token()
    
    # Teams 채팅에 메시지 전송
    url = f"{settings.graph_host}/chats/{chat_id}/messages"
    headers = {
        "Authorization": f"Bearer {token['access_token']}",
        "Content-Type": "application/json",
    }
    
    body = {
        "body": {
            "contentType": "html",
            "content": html_content
        }
    }
    
    response = requests.post(url, headers=headers, json=body, timeout=60)
    response.raise_for_status()
    
    return response.json()


