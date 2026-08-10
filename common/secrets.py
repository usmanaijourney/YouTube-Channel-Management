"""Secrets-manager client wrapper (stands in for Vault/AWS Secrets Manager, §8).

Each Channel Manager only ever requests secrets under its own `channel-{id}/*`
path — enforced here by requiring the caller to pass `channel_id` and refusing
to serve any path outside that prefix. In production this maps to an IAM
policy on the secrets-manager side, not just an app-level check.

`youtube_oauth` is wired to real credentials: a refresh token saved locally by
scripts/authorize_youtube.py (under secrets/{channel_id}/youtube_token.json) is
exchanged for a fresh, short-lived access token on every call — the long-lived
refresh token itself is never handed to a caller. Everything else still comes
from the mock vault until it gets the same treatment (TTS needs no entry here —
edge-tts, the current provider, requires no credentials at all).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from common.errors import PermanentError

_SECRETS_DIR = Path("secrets")

_MOCK_VAULT: dict[str, dict[str, str]] = {
    "channel-001/whatsapp_notify_target": {"recipient": "+10000000001"},
}


def _refresh_youtube_token(channel_id: str) -> str:
    token_path = _SECRETS_DIR / channel_id / "youtube_token.json"
    if not token_path.exists():
        raise PermanentError(
            f"no YouTube OAuth token on file for '{channel_id}' — "
            f"run scripts/authorize_youtube.py --channel-id {channel_id} first"
        )
    data = json.loads(token_path.read_text())
    credentials = Credentials(
        token=None,
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data["scopes"],
    )
    credentials.refresh(Request())
    return credentials.token


async def get_secret(channel_id: str, secret_path: str) -> dict[str, str]:
    if not secret_path.startswith(f"{channel_id}/"):
        raise PermanentError(
            f"secrets access denied: channel '{channel_id}' may not read '{secret_path}'"
        )

    if secret_path == f"{channel_id}/youtube_oauth":
        access_token = await asyncio.to_thread(_refresh_youtube_token, channel_id)
        return {"access_token": access_token}

    secret = _MOCK_VAULT.get(secret_path)
    if secret is None:
        raise PermanentError(f"secret not found: {secret_path}")
    return secret
