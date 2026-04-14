"""Gmail API operations — fetch, archive, label, delete.

Tylko metadane + snippet (nie pełne body) — zgodnie z PRD.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from googleapiclient.errors import HttpError


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
    """From: 'Name <x@y.com>' or 'x@y.com' → (full, domain)."""
    full = from_header.strip()
    email = full
    if "<" in full and ">" in full:
        email = full.split("<", 1)[1].split(">", 1)[0]
    domain = email.split("@", 1)[1].lower() if "@" in email else ""
    return full, domain


def list_message_ids(service: Any, query: str, max_results: int = 500) -> list[str]:
    """Gmail search query — np. 'newer_than:1d', 'in:inbox', 'in:trash'."""
    ids: list[str] = []
    page_token: str | None = None
    while True:
        req = service.users().messages().list(
            userId="me", q=query, maxResults=min(500, max_results - len(ids)),
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


def ensure_label(service: Any, name: str) -> str:
    """Tworzy label jeśli nie istnieje, zwraca ID."""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lbl in labels:
        if lbl["name"] == name:
            return lbl["id"]
    created = service.users().labels().create(
        userId="me",
        body={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
    ).execute()
    return created["id"]


def archive_with_label(service: Any, message_ids: list[str], label_id: str) -> None:
    """Usuwa INBOX, dodaje label. Batch po 1000."""
    for i in range(0, len(message_ids), 1000):
        batch = message_ids[i : i + 1000]
        service.users().messages().batchModify(
            userId="me",
            body={"ids": batch, "addLabelIds": [label_id], "removeLabelIds": ["INBOX"]},
        ).execute()


def restore_to_inbox(service: Any, message_ids: list[str], remove_label_id: str) -> None:
    for i in range(0, len(message_ids), 1000):
        batch = message_ids[i : i + 1000]
        service.users().messages().batchModify(
            userId="me",
            body={"ids": batch, "addLabelIds": ["INBOX"], "removeLabelIds": [remove_label_id]},
        ).execute()


def trash_messages(service: Any, message_ids: list[str]) -> None:
    for mid in message_ids:
        try:
            service.users().messages().trash(userId="me", id=mid).execute()
        except HttpError as e:
            if e.resp.status != 404:
                raise
