"""Cron 06:30 — trwałe kasowanie maili z labela `_AI_TRASH` starszych niż 7 dni.

Sesja 1: stub. Pełna implementacja w Sesji 3.
"""
from http.server import BaseHTTPRequestHandler
import json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "stage": "stub"}).encode())
