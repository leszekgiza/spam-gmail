"""Cron 03:00 — pobranie nowych maili z Gmail API do Neon Postgres.

Sesja 1: stub. Pełna implementacja w Sesji 2.
"""
from http.server import BaseHTTPRequestHandler
import json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "stage": "stub"}).encode())
