"""Gmail OAuth — dwutryb:

1. **CLI (bootstrap/localny)**: interaktywny OAuth flow z `credentials.json`, zapis `token.json`
   z refresh_token. Uruchamiane raz ręcznie z lokalnego PC.

2. **Serverless (Vercel)**: odczyt `GMAIL_REFRESH_TOKEN` + `GMAIL_CLIENT_ID` + `GMAIL_CLIENT_SECRET`
   z env vars, odświeżenie access tokena przy każdym wywołaniu funkcji.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _creds_from_env() -> Credentials:
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
    return creds


def _creds_from_file(token_path: Path, credentials_path: Path) -> Credentials:
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        return creds

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json())
    return creds


def get_service() -> Any:
    """Zwraca uwierzytelniony Gmail API service. W runtime Vercela z env; lokalnie z pliku."""
    if os.getenv("VERCEL"):
        creds = _creds_from_env()
    else:
        root = Path(__file__).resolve().parents[2]
        creds = _creds_from_file(
            token_path=root / ".secrets" / "token.json",
            credentials_path=root / ".secrets" / "credentials.json",
        )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def print_env_block_from_local_token() -> None:
    """CLI helper: po OAuth flow wypisuje blok env vars do wklejenia do Vercela."""
    root = Path(__file__).resolve().parents[2]
    token_path = root / ".secrets" / "token.json"
    credentials_path = root / ".secrets" / "credentials.json"
    creds = _creds_from_file(token_path, credentials_path)

    client_info = json.loads(credentials_path.read_text())
    installed = client_info.get("installed") or client_info.get("web") or {}
    print("\n=== Wklej do Vercel env vars (Production + Preview) ===")
    print(f"GMAIL_CLIENT_ID={installed.get('client_id', '')}")
    print(f"GMAIL_CLIENT_SECRET={installed.get('client_secret', '')}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("===============================================\n")


if __name__ == "__main__":
    print_env_block_from_local_token()
