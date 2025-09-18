from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests


class GraphClient:
    def __init__(self, graph_host: str, access_token: str) -> None:
        self.graph_host = graph_host.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def get_schedule(
        self,
        users: List[str],
        start: str,
        end: str,
        interval_minutes: int = 30,
        timezone: str = "Asia/Seoul",
    ) -> Dict[str, Any]:
        url = f"{self.graph_host}/me/calendar/getSchedule"
        body = {
            "schedules": users,
            "startTime": {"dateTime": start, "timeZone": timezone},
            "endTime": {"dateTime": end, "timeZone": timezone},
            "availabilityViewInterval": interval_minutes,
        }
        resp = requests.post(url, headers=self._headers, data=json.dumps(body), timeout=60)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def availability_to_slots(response: Dict[str, Any], interval_minutes: int) -> Dict[str, List[str]]:
        # Returns mapping of user -> availabilityView string (e.g., '000110...')
        result: Dict[str, List[str]] = {}
        for sched in response.get("value", []):
            user = sched.get("scheduleId")
            view = sched.get("availabilityView", "")
            result[user] = list(view)
        return result

    # --- Teams messaging via Microsoft Graph (delegated permissions required) ---
    def send_channel_message(self, team_id: str, channel_id: str, html_content: str) -> Dict[str, Any]:
        url = f"{self.graph_host}/teams/{team_id}/channels/{channel_id}/messages"
        body = {
            "subject": None,
            "body": {"contentType": "html", "content": html_content},
        }
        resp = requests.post(url, headers=self._headers, data=json.dumps(body), timeout=60)
        resp.raise_for_status()
        return resp.json()

    def send_chat_message(self, chat_id: str, html_content: str) -> Dict[str, Any]:
        url = f"{self.graph_host}/chats/{chat_id}/messages"
        body = {
            "body": {"contentType": "html", "content": html_content},
        }
        resp = requests.post(url, headers=self._headers, data=json.dumps(body), timeout=60)
        resp.raise_for_status()
        return resp.json()

    def forward_event(self, event_id: str, recipients: List[str], comment: str | None = None) -> None:
        url = f"{self.graph_host}/me/events/{event_id}/forward"
        body = {
            "comment": comment or "",
            "toRecipients": [{"emailAddress": {"address": r}} for r in recipients],
        }
        resp = requests.post(url, headers=self._headers, data=json.dumps(body), timeout=60)
        resp.raise_for_status()

    def send_mail(self, to: List[str], subject: str, body_html: str, save_to_sent: bool = True) -> None:
        url = f"{self.graph_host}/me/sendMail"
        body = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": [{"emailAddress": {"address": r}} for r in to],
            },
            "saveToSentItems": save_to_sent,
        }
        resp = requests.post(url, headers=self._headers, data=json.dumps(body), timeout=60)
        resp.raise_for_status()

    def create_event(
        self,
        subject: str,
        start: str,
        end: str,
        timezone: str,
        attendees: Optional[List[str]] = None,
        body: Optional[str] = None,
        location: Optional[str] = None,
        send_invitations: bool = True,
    ) -> Dict[str, Any]:
        url = f"{self.graph_host}/me/events"
        if send_invitations and attendees:
            url += "?sendInvitations=true"
        event: Dict[str, Any] = {
            "subject": subject,
            "start": {"dateTime": start, "timeZone": timezone},
            "end": {"dateTime": end, "timeZone": timezone},
        }
        if attendees:
            event["attendees"] = [
                {"emailAddress": {"address": a}, "type": "required"} for a in attendees
            ]
        if body:
            event["body"] = {"contentType": "HTML", "content": body}
        if location:
            event["location"] = {"displayName": location}

        resp = requests.post(url, headers=self._headers, data=json.dumps(event), timeout=60)
        resp.raise_for_status()
        return resp.json()

    def update_event(
        self,
        event_id: str,
        location: Optional[str] = None,
        body_append: Optional[str] = None,
    ) -> None:
        url = f"{self.graph_host}/me/events/{event_id}"
        patch: Dict[str, Any] = {}
        if location:
            patch["location"] = {"displayName": location}
        if body_append:
            patch["body"] = {
                "contentType": "HTML",
                "content": body_append,
            }
        resp = requests.patch(url, headers=self._headers, data=json.dumps(patch), timeout=60)
        resp.raise_for_status()

    # Invitations are sent at creation using sendInvitations=true; no separate send call


