"""Real YouTube Data API v3 client (doc §13).

`access_token` is a short-lived, scoped token minted just-in-time by
common/secrets.py per §8 — never the raw OAuth client secret, and never
passed to an LLM. Defaults to `privacyStatus=private` so nothing this
pipeline uploads goes public without a deliberate config change.
"""
from __future__ import annotations

import asyncio
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from common.errors import PermanentError, TransientError

# 403 covers YouTube's quota/rate-limit responses, not just permission errors —
# treated as transient here since a retry after backoff is the right response.
_TRANSIENT_HTTP_STATUSES = {403, 429, 500, 502, 503, 504}


def _upload_sync(video_path: str, title: str, description: str, access_token: str,
                  privacy_status: str, category_id: str) -> dict[str, Any]:
    credentials = Credentials(token=access_token)
    youtube = build("youtube", "v3", credentials=credentials)

    body = {
        "snippet": {"title": title, "description": description, "categoryId": category_id},
        "status": {"privacyStatus": privacy_status},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()
    return response


async def upload_video(video_path: str, title: str, description: str, access_token: str, *,
                        privacy_status: str = "private", category_id: str = "22") -> dict[str, Any]:
    if not access_token:
        raise PermanentError("YouTube API: missing access token")

    try:
        response = await asyncio.to_thread(
            _upload_sync, video_path, title, description, access_token, privacy_status, category_id,
        )
    except HttpError as e:
        status = e.resp.status if e.resp is not None else None
        if status in _TRANSIENT_HTTP_STATUSES:
            raise TransientError(f"YouTube API transient error ({status}): {e}") from e
        raise PermanentError(f"YouTube API permanent error ({status}): {e}") from e

    youtube_video_id = response["id"]
    return {
        "youtube_video_id": youtube_video_id,
        "youtube_url": f"https://youtube.com/watch?v={youtube_video_id}",
        "title": title,
    }
