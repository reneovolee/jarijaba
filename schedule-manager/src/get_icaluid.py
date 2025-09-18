from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import urllib.parse

import requests

# Allow running as a script
if __package__ is None or __package__ == "":
    this_dir = Path(__file__).resolve().parent
    sys.path.append(str(this_dir))
    from env import load_env  # type: ignore
    from config import load_settings  # type: ignore
    from auth import DeviceCodeTokenProvider  # type: ignore
else:
    from .env import load_env
    from .config import load_settings
    from .auth import DeviceCodeTokenProvider


def main() -> None:
    parser = argparse.ArgumentParser("get-icaluid")
    parser.add_argument("--eventId", required=True, help="Organizer's event ID")
    args = parser.parse_args()

    load_env()
    settings = load_settings()
    token = DeviceCodeTokenProvider(settings.tenant_id, settings.client_id).acquire_token()

    eid = urllib.parse.quote(args.eventId, safe="")
    url = f"{settings.graph_host}/me/events/{eid}?$select=iCalUId,id"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token['access_token']}"}, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    print(json.dumps({"id": data.get("id"), "iCalUId": data.get("iCalUId")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


