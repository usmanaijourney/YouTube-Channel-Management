"""API-key auth for the dashboard API — single-operator model (no user/role tables).

Key resolution order: `DASHBOARD_API_KEY` env var (the "environment-based
secrets" the platform spec asks for) first; if unset, falls back to a local
key file (secrets/dashboard_api_key.txt, gitignored, auto-generated on first
use) — this avoids relying on env-var propagation across every process that
might launch the server (a plain shell, a browser preview harness, etc.),
matching the project's existing file-based local-secrets convention.
"""
from __future__ import annotations

import os
import secrets as pysecrets
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER_NAME = "X-API-Key"
_KEY_FILE = Path("secrets") / "dashboard_api_key.txt"

_api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


def _load_or_create_key_file() -> str:
    if _KEY_FILE.exists():
        key = _KEY_FILE.read_text().strip()
        if key:
            return key
    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    key = pysecrets.token_urlsafe(32)
    _KEY_FILE.write_text(key)
    return key


def get_expected_api_key() -> str:
    return os.environ.get("DASHBOARD_API_KEY") or _load_or_create_key_file()


async def require_api_key(provided: Optional[str] = Security(_api_key_header)) -> None:
    expected = get_expected_api_key()
    if not provided or provided != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or missing API key")
