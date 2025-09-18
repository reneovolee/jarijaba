from __future__ import annotations

import base64
import hmac
import os
from hashlib import sha256
from urllib.parse import urlencode


def _secret() -> bytes:
    key = os.getenv("RSVP_SECRET", "dev-secret-change-me").encode("utf-8")
    return key


def sign_params(params: dict) -> str:
    # Create stable query string
    q = urlencode(sorted(params.items()))
    sig = hmac.new(_secret(), q.encode("utf-8"), sha256).digest()
    return base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")


def verify_params(params: dict, signature: str) -> bool:
    expected = sign_params(params)
    return hmac.compare_digest(expected, signature)


def build_rsvp_url(base_url: str, event_id: str | None, user: str | None, response: str, **extras) -> str:
    params = {"resp": response}
    if event_id:
        params["eventId"] = event_id
    if user:
        params["user"] = user
    # include any extra key-values (e.g., subject/start/end/timezone/location/attendees)
    for k, v in extras.items():
        if v is not None:
            params[k] = v
    sig = sign_params(params)
    params["sig"] = sig
    return f"{base_url.rstrip('/')}/rsvp?{urlencode(params)}"


