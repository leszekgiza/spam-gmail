"""Gmail client dla Vercel Python runtime — OAuth z env vars, operacje metadane/trash.

Zwendorowane z packages/gmail/auth.py + packages/gmail/operations.py,
żeby Vercel bundler (Root Directory = apps/web) mógł to zapakować.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_service() -> Any:
    client_id = os.environ["GMAIL_CLIENT_ID"]
    client_secret = os.environ["GMAIL_CLIENT_SECRET"]
    refresh_token = os.environ["GMAIL_REFRESH_TOKEN"]
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


@dataclass
class EmailMeta:
    id: str
    thread_id: str
    sender: str
    sender_domain: str
    subject: str
    snippet: str
    labels: list[str] = field(default_factory=list)
    received_at: datetime | None = None


def _header(headers: list[dict[str, str]], name: str) -> str:
    name_lower = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_lower:
            return h.get("value", "")
    return ""


def _parse_sender(from_header: str) -> tuple[str, str]:
    full = from_header.strip()
    email = full
    if "<" in full and ">" in full:
        email = full.split("<", 1)[1].split(">", 1)[0]
    domain = email.split("@", 1)[1].lower() if "@" in email else ""
    return full, domain


def list_message_ids(service: Any, query: str, max_results: int = 500) -> list[str]:
    ids: list[str] = []
    page_token: str | None = None
    while True:
        req = service.users().messages().list(
            userId="me", q=query,
            maxResults=min(500, max_results - len(ids)),
            pageToken=page_token,
        )
        resp = req.execute()
        for m in resp.get("messages", []):
            ids.append(m["id"])
            if len(ids) >= max_results:
                return ids
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def get_metadata(service: Any, message_id: str) -> EmailMeta:
    msg = service.users().messages().get(
        userId="me", id=message_id, format="metadata",
        metadataHeaders=["From", "Subject", "Date"],
    ).execute()
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    from_h = _header(headers, "From")
    subject = _header(headers, "Subject")
    full_sender, domain = _parse_sender(from_h)

    received = None
    internal_ms = msg.get("internalDate")
    if internal_ms:
        received = datetime.fromtimestamp(int(internal_ms) / 1000, tz=timezone.utc)

    return EmailMeta(
        id=msg["id"],
        thread_id=msg.get("threadId", ""),
        sender=full_sender,
        sender_domain=domain,
        subject=subject,
        snippet=msg.get("snippet", "")[:200],
        labels=msg.get("labelIds", []),
        received_at=received,
    )


def iter_metadata(service: Any, message_ids: Iterable[str]) -> Iterable[EmailMeta]:
    for mid in message_ids:
        try:
            yield get_metadata(service, mid)
        except HttpError as e:
            if e.resp.status == 404:
                continue
            raise


def trash_messages(service: Any, message_ids: list[str]) -> None:
    for mid in message_ids:
        try:
            service.users().messages().trash(userId="me", id=mid).execute()
        except HttpError as e:
            if e.resp.status != 404:
                raise
