"""Gmail client dla Vercel Python runtime — OAuth z env vars, operacje metadane/trash.

Zwendorowane z packages/gmail/auth.py + packages/gmail/operations.py,
żeby Vercel bundler (Root Directory = apps/web) mógł to zapakować.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from email.utils import parseaddr
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


# --- Ochrona korespondencji: jesli Leszek pisal do nadawcy, to nie spam ---
# Decyzja 2026-10-17: odpowiedzi instalatorow klimatyzacji i dealerow aut lecialy
# do kosza (ML p0.8-0.98), mimo ze to byly odpowiedzi na jego zapytania.

# Adresy automatyczne — nawet jesli kiedys na nie odpisal (np. unsubscribe), to nie rozmowa.
# Po domenie celowo NIE dopasowujemy: mail do kogos z allegro.pl/mbank.pl chronilby
# wszystkie ich powiadomienia (sprawdzone na 30 dniach: 252 falszywe trafienia).
_AUTOMATED_LOCAL = re.compile(
    r"^(no-?reply|do-?not-?reply|notifications?|newsletters?|mailings?|marketing|news|updates?|powiadomienia|message)\b", re.I,
)


# Scisly addr-spec — adres trafia do zapytania Gmaila, wiec nie wpuszczamy spacji,
# cudzyslowow, nawiasow ani operatorow (np. "a@b.pl OR in:inbox").
_STRICT_ADDR = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")


def _sender_addr(sender: str) -> str | None:
    """Adres z naglowka From albo None, jesli nie wyglada jak prawdziwy adres."""
    _, addr = parseaddr(sender or "")
    addr = addr.strip().lower()
    return addr if _STRICT_ADDR.match(addr) else None


def _has_sent(service: Any, query: str) -> bool:
    resp = service.users().messages().list(userId="me", q=query, maxResults=1).execute()
    return bool(resp.get("messages"))


def sent_thread_ids(service: Any, days: int = 730) -> set[str]:
    """Wątki, w których Leszek cokolwiek wysłał. messages.list zwraca threadId,
    więc to ~N/500 zapytań zamiast threads.get per kandydat."""
    threads: set[str] = set()
    page_token: str | None = None
    while True:
        resp = service.users().messages().list(
            userId="me", q=f"in:sent newer_than:{days}d", maxResults=500, pageToken=page_token,
        ).execute()
        threads.update(m["threadId"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            return threads


def has_correspondence(
    service: Any, meta: EmailMeta, sent_threads: set[str], cache: dict[str, bool],
) -> str | None:
    """Zwraca powod ('thread'/'address') jesli byla korespondencja, inaczej None.

    `sent_threads` z sent_thread_ids(); `cache` trzymamy na caly przebieg crona
    — jedno zapytanie per adres nadawcy.
    """
    if meta.thread_id in sent_threads:
        return "thread"
    addr = _sender_addr(meta.sender)
    if addr is None or _AUTOMATED_LOCAL.match(addr.split("@", 1)[0]):
        return None
    # Domena adresu musi zgadzac sie z sender_domain z parsera metadanych.
    if meta.sender_domain and addr.split("@", 1)[1] != meta.sender_domain.lower():
        return None
    if addr not in cache:
        cache[addr] = _has_sent(service, f'in:sent to:"{addr}"')
    return "address" if cache[addr] else None
