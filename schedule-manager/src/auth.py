from __future__ import annotations

import os
from typing import Dict, List, Optional

import msal


class DeviceCodeTokenProvider:
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        scopes: Optional[List[str]] = None,
        token_cache_path: str = ".token_cache.bin",
    ) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.scopes = scopes or [
            "User.Read",
            "Calendars.ReadWrite",
        ]
        # Allow adding extra scopes via env (e.g., Teams messaging):
        # AZURE_SCOPES="User.Read Calendars.ReadWrite Chat.ReadWrite ChatMessage.Send ChannelMessage.Send"
        extra = os.getenv("AZURE_SCOPES")
        if extra:
            # Split by whitespace or comma
            parts = [p.strip() for p in extra.replace(",", " ").split() if p.strip()]
            # Only extend if user provided anything
            if parts:
                self.scopes = parts
        self.token_cache_path = token_cache_path

        self._cache = msal.SerializableTokenCache()
        if os.path.exists(self.token_cache_path):
            self._cache.deserialize(open(self.token_cache_path, "r", encoding="utf-8").read())

        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self._app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=authority,
            token_cache=self._cache,
        )

    def _save_cache(self) -> None:
        with open(self.token_cache_path, "w", encoding="utf-8") as f:
            f.write(self._cache.serialize())

    def acquire_token(self) -> Dict[str, str]:
        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(self.scopes, account=accounts[0])
            if result and "access_token" in result:
                return result

        flow = self._app.initiate_device_flow(scopes=self.scopes)
        if "user_code" not in flow:
            # Surface MSAL error details to help diagnose (e.g., public client disabled, invalid scopes)
            error = flow.get("error")
            error_description = flow.get("error_description")
            raise RuntimeError(
                f"Failed to create device flow. error={error} description={error_description} scopes={self.scopes} tenant={self.tenant_id}"
            )

        print(flow["message"])  # Prompt user to authenticate
        result = self._app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            raise RuntimeError(f"Authentication failed: {result}")

        self._save_cache()
        return result


