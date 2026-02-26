from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from server.domain import ActionRequest
from server.persistence import AwanDbRepository, InMemoryRepository
from server.service import GameService


def build_service() -> GameService:
    endpoint = os.getenv("AWANDB_ENDPOINT")
    username = os.getenv("AWANDB_USERNAME", "admin")
    password = os.getenv("AWANDB_PASSWORD", "admin")

    if endpoint:
        try:
            repository = AwanDbRepository(endpoint=endpoint, username=username, password=password)
            print(f"Using AwanDB repository at {endpoint}")
        except Exception as exc:
            print(f"Falling back to in-memory repository: {exc}")
            repository = InMemoryRepository()
    else:
        repository = InMemoryRepository()

    return GameService(repository=repository)


SERVICE = build_service()


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/actions":
            self._handle_actions()
            return
        if self.path == "/bots/tick":
            self._handle_bot_tick()
            return
        if self.path == "/snapshot":
            self._handle_snapshot()
            return
        self._send_json(404, {"error": "not found"})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/state":
            self._handle_state(parsed)
            return
        if parsed.path == "/metrics":
            self._handle_metrics(parsed)
            return
        if parsed.path == "/sessions":
            self._send_json(200, SERVICE.list_sessions())
            return
        self._send_json(404, {"error": "not found"})

    def _handle_actions(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        try:
            action = ActionRequest(**payload)
        except TypeError as exc:
            self._send_json(400, {"error": f"invalid action payload: {exc}"})
            return

        result = SERVICE.submit_action(action)
        self._send_json(200, result)

    def _handle_bot_tick(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        if "session_id" not in payload or "tick" not in payload:
            self._send_json(400, {"error": "session_id and tick are required"})
            return

        session_id = payload["session_id"]
        tick = int(payload["tick"])
        result = SERVICE.tick_bots(session_id=session_id, tick=tick)
        self._send_json(200, {"bot_results": result})


    def _handle_snapshot(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        session_id = payload.get("session_id")
        if not session_id:
            self._send_json(400, {"error": "session_id is required"})
            return
        target_path = payload.get("target_path")
        result = SERVICE.create_snapshot(session_id=session_id, target_path=target_path)
        status = 200 if "error" not in result else 404
        self._send_json(status, result)

    def _handle_state(self, parsed) -> None:
        query = parse_qs(parsed.query)
        session_id = query.get("session_id", [""])[0]
        if not session_id:
            self._send_json(400, {"error": "session_id is required"})
            return
        result = SERVICE.get_state(session_id=session_id)
        self._send_json(200, result)

    def _handle_metrics(self, parsed) -> None:
        query = parse_qs(parsed.query)
        session_id = query.get("session_id", [""])[0]
        if not session_id:
            self._send_json(400, {"error": "session_id is required"})
            return
        self._send_json(200, SERVICE.get_metrics(session_id=session_id))

    def _read_json_body(self) -> dict | None:
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json body"})
            return None

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run() -> None:
    host = os.getenv("MMORTS_HOST", "0.0.0.0")
    port = int(os.getenv("MMORTS_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), RequestHandler)
    print(f"MMORTS server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
