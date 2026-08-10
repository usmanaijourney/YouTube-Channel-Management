"""One-time OAuth authorization for a channel's YouTube upload access.

Run once per channel: opens a browser for the channel owner to sign in and
grant upload access, then stores a refresh token locally under secrets/{channel_id}/.
Stands in for the Vault/Secrets Manager in doc §8 for the MVP — migrate to a
real secrets manager before this goes anywhere near production.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel-id", default="channel-001")
    args = parser.parse_args()

    channel_dir = Path("secrets") / args.channel_id
    client_secret_path = channel_dir / "youtube_client_secret.json"
    token_path = channel_dir / "youtube_token.json"

    if not client_secret_path.exists():
        raise SystemExit(f"missing {client_secret_path} — download OAuth client credentials first")

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
    print("Opening a browser window — sign in and approve access for the YouTube channel "
          "you want this to manage. Waiting for you to complete that...")
    credentials = flow.run_local_server(port=0)

    token_path.write_text(json.dumps({
        "refresh_token": credentials.refresh_token,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "token_uri": credentials.token_uri,
        "scopes": credentials.scopes,
    }, indent=2))

    print(f"Saved refresh token to {token_path}")


if __name__ == "__main__":
    main()
