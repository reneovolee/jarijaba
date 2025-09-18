from __future__ import annotations

import json
from typing import Any, Dict

import requests


def trigger_flow(flow_url: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
    headers = {"Content-Type": "application/json"}
    resp = requests.post(flow_url, headers=headers, data=json.dumps(payload), timeout=30)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:  # noqa: BLE001
        return None


