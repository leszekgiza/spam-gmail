"""Cron 06:00 — klasyfikacja nowych maili + (opcjonalnie) archiwizacja.

Sesja 1: stub. Pełna implementacja w Sesji 3.
"""
from http.server import BaseHTTPRequestHandler
import json
import os


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        shadow = os.getenv("SHADOW_MODE", "true").lower() == "true"
        auto_delete = os.getenv("AUTO_DELETE", "false").lower() == "true"
        emergency = os.getenv("EMERGENCY_STOP", "false").lower() == "true"

        payload = {
            "status": "ok",
            "stage": "stub",
            "shadow_mode": shadow,
            "auto_delete": auto_delete,
            "emergency_stop": emergency,
            "note": "Sesja 1 scaffold — classifier not yet implemented",
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())
