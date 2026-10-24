"""The suite's authenticated loopback bridge, owned by the running TUI."""

from __future__ import annotations

import hmac
import ipaddress
import json
import os
import re
import secrets
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .activity import clean
from .config import data_dir
from . import __version__

MAX_BODY = 65_536
FRESH_SECONDS = 45


class ControlConflict(ValueError):
    pass


def pairing_file() -> Path:
    return data_dir() / "browser-bridge.json"


def load_pairing(port: int = 5643) -> dict:
    path = pairing_file()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if re.fullmatch(r"[a-f0-9]{64}", value.get("token", "")):
            return {"port": int(value.get("port", port)), "token": value["token"]}
    except (OSError, ValueError, TypeError):
        pass
    value = {"port": port, "token": secrets.token_hex(32)}
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream)
    return value


def _identifier(value: object, limit: int = 120) -> str:
    text = str(value or "")
    if not re.fullmatch(r"[a-zA-Z0-9_.:-]{1," + str(limit) + "}", text):
        raise ValueError("Invalid identity")
    return text


def _digest(value: object) -> str:
    text = str(value or "")
    if text and not re.fullmatch("[a-f0-9]{64}", text):
        raise ValueError("Invalid digest")
    return text


class BridgeState:
    def __init__(self):
        self.lock = threading.RLock()
        self.active = False
        self.include_titles = False
        self.inventory_until = 0.0
        self.owner_seen = 0.0
        self.profiles: dict[str, dict] = {}
        self.agents: dict[str, dict] = {}
        self.stopping = False
        self.timer = None
        self.timer_seen = 0.0
        self.control_revision = secrets.randbelow(2**48) + 2**48  # Safe JS integer; unique across restarts.
        self.controls = deque()
        self.client_seen = 0.0

    def client_connected(self):
        with self.lock:
            return self.client_seen > 0 and time.monotonic() - self.client_seen <= 45

    def publish_timer(self, snapshot: dict):
        with self.lock:
            snapshot = dict(snapshot)
            snapshot["can_control"] = bool(snapshot.get("can_control") and not self.controls)
            identity = ("status", "session_id", "name", "kind", "can_control")
            if self.timer is None or any(self.timer.get(key) != snapshot.get(key) for key in identity):
                self.control_revision += 1
            snapshot["revision"] = self.control_revision
            self.timer = snapshot
            self.timer_seen = time.monotonic()

    def queue_control(self, payload: dict):
        with self.lock:
            timer = self.timer
            revision = payload.get("revision")
            sid = payload.get("session_id")
            if (not isinstance(revision, int) or isinstance(revision, bool)
                    or sid is not None and (not isinstance(sid, int) or isinstance(sid, bool))):
                raise ValueError("Invalid timer identity")
            if (timer is None or time.monotonic() - self.timer_seen > 3 or self.stopping
                    or not timer["can_control"] or revision != timer["revision"] or sid != timer["session_id"]):
                raise ControlConflict("Session changed or Breadcrumbs is busy; refresh and try again")
            action = payload.get("action")
            allowed = {"start": ("ready",), "pause": ("running",), "resume": ("paused",),
                       "finish": ("running", "paused")}
            if action not in allowed:
                raise ValueError("Unknown timer action")
            if timer["status"] not in allowed[action] or action != "start" and sid is None:
                raise ControlConflict("Action no longer applies to this session")
            self.controls.append(dict(action=action, session_id=sid, status=timer["status"]))
            timer["can_control"] = False
            self.control_revision += 1
            timer["revision"] = self.control_revision

    def take_controls(self) -> list[dict]:
        with self.lock:
            result = list(self.controls)
            self.controls.clear()
            return result

    def publish(self, active: bool, include_titles: bool, inventory: bool = False):
        with self.lock:
            if not active:
                for record in self.profiles.values():
                    record.update(focused=False, title="", domain="", page_key="", title_key="")
            if not inventory:
                for record in self.profiles.values():
                    record["tabs"] = []
            if not include_titles:
                for record in self.profiles.values():
                    record["title"] = ""
            self.active = active
            self.include_titles = include_titles
            self.owner_seen = time.monotonic()
            self.inventory_until = time.monotonic() + 3 if inventory else 0.0

    def status(self) -> dict:
        with self.lock:
            owner_fresh = time.monotonic() - self.owner_seen <= 3
            timer = dict(self.timer) if self.timer else None
            if timer and (time.monotonic() - self.timer_seen > 3 or self.stopping):
                timer["can_control"] = False
            now = time.monotonic()
            records = [record for record in self.profiles.values() if now - record["received_at"] <= FRESH_SECONDS]
            browser = dict(reports=len(records), focused=sum(bool(record["focused"]) for record in records),
                versions=sorted({record.get("extension_version") or "unreported" for record in records}),
                last_report_seconds=round(min((now-record["received_at"] for record in records), default=0), 1) if records else None)
            return dict(version=1, app_version=__version__, required_extension_version=__version__, browser_diagnostics=browser,
                        pairing=True, active=self.active and owner_fresh and not self.stopping,
                        inventory_requested=time.monotonic() < self.inventory_until and not self.stopping,
                        include_titles=self.include_titles, stopping=self.stopping, timer=timer)

    def receive_browser(self, payload: dict):
        profile = _identifier(payload.get("profile_id"))
        instance = _identifier(payload.get("browser_instance_id"))
        sent_at = float(payload.get("sent_at", 0))
        if not 0 <= time.time() - sent_at <= 120:
            raise ValueError("Stale browser event")
        with self.lock:
            policy = self.status()
            old = self.profiles.get(profile)
            if old and sent_at < old["sent_at"]:
                return
            if profile not in self.profiles and len(self.profiles) >= 32:
                oldest = min(self.profiles, key=lambda key: self.profiles[key]["received_at"])
                del self.profiles[oldest]
            permitted = policy["active"] or policy["inventory_requested"]
            record = dict(profile_id=profile, browser_instance_id=instance,
                          sent_at=sent_at, received_at=time.monotonic(), focused=False,
                          tab_id=None, window_id=None, domain="", title="", page_key="", title_key="",
                          incognito=bool(payload.get("incognito")), tabs=[])
            record["extension_version"] = _identifier(payload["extension_version"], 40) if payload.get("extension_version") else ""
            # Closed/paused sessions do not retain incoming metadata, even from a stale extension.
            if permitted:
                record["focused"] = payload.get("focused") is True
                if not record["incognito"]:
                    record.update(self._tab(payload, policy["include_titles"]))
                    if policy["inventory_requested"]:
                        tabs = payload.get("tabs", [])
                        if not isinstance(tabs, list) or len(tabs) > 256:
                            raise ValueError("Invalid inventory")
                        record["tabs"] = [
                            dict(self._tab(tab, True), profile_id=profile, browser_instance_id=instance)
                            for tab in tabs if isinstance(tab, dict) and not tab.get("incognito")
                        ]
            self.profiles[profile] = record

    @staticmethod
    def _tab(tab: dict, titles: bool) -> dict:
        domain = str(tab.get("domain", "")).lower().removeprefix("www.").rstrip(".")
        if domain and not re.fullmatch(r"[a-z0-9.-]{1,253}", domain):
            try:
                domain = ipaddress.IPv6Address(domain.removeprefix("[").removesuffix("]")).compressed
            except ipaddress.AddressValueError as error:
                raise ValueError("Invalid domain") from error
        tab_id, window_id = tab.get("tab_id"), tab.get("window_id")
        if any(value is not None and (not isinstance(value, int) or isinstance(value, bool)) for value in (tab_id, window_id)):
            raise ValueError("Invalid browser IDs")
        return dict(domain=domain, title=clean(tab.get("title"), 240) if titles else "",
                    page_key=_digest(tab.get("page_key")), title_key=_digest(tab.get("title_key")),
                    tab_id=tab_id, window_id=window_id)

    def browser_records(self) -> list[dict]:
        with self.lock:
            now = time.monotonic()
            return [dict(record) for record in self.profiles.values()
                    if now - record["received_at"] <= FRESH_SECONDS]

    def browser_tabs(self) -> list[dict]:
        if not self.status()["inventory_requested"]:
            return []
        return [tab for record in self.browser_records() for tab in record["tabs"]]

    def register_agent(self, target: dict) -> str:
        lease = secrets.token_hex(12)
        with self.lock:
            self.agents[lease] = dict(target, lease=lease, enabled=True,
                                     last_seen=0.0, console_key="", problem="")
        return lease

    def agent_permission(self, lease: str) -> dict:
        with self.lock:
            agent = self.agents.get(lease)
            return dict(active=bool(agent and agent["enabled"] and self.status()["active"]),
                        stopping=self.stopping or not agent or not agent["enabled"])

    def agent_heartbeat(self, payload: dict):
        lease = _identifier(payload.get("lease"))
        with self.lock:
            if lease not in self.agents:
                raise ValueError("Unknown marker lease")
            self.agents[lease].update(last_seen=time.monotonic(),
                                     console_key=clean(payload.get("console_key"), 120),
                                     problem=clean(payload.get("problem"), 160))

    def agent_records(self) -> list[dict]:
        with self.lock:
            current = [dict(agent) for agent in self.agents.values()
                    if agent["enabled"] and time.monotonic() - agent["last_seen"] <= 4 and not agent["problem"]]
            return [agent for agent in current if agent["console_key"] and sum(
                other["console_key"] == agent["console_key"] for other in current) == 1]

    def agent_problem(self, selected_ids: set[str]) -> str:
        with self.lock:
            for agent in reversed(list(self.agents.values())):
                if (agent["id"] in selected_ids and agent["enabled"] and agent["problem"]
                        and time.monotonic() - agent["last_seen"] <= 4):
                    return agent["problem"]
        return ""


class BridgeServer:
    def __init__(self, port: int = 5643, token: str | None = None):
        credentials = load_pairing(port) if token is None else {"port": port, "token": token}
        self.token = credentials["token"]
        self.state = BridgeState()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass  # URLs and payloads must not reach terminal logs.

            def _origin(self):
                origin = self.headers.get("Origin")
                return origin if origin and re.fullmatch(r"chrome-extension://[a-p]{32}", origin) else None

            def _authorized(self):
                origin = self.headers.get("Origin")
                if origin and self._origin() is None:
                    return False
                supplied = self.headers.get("Authorization", "")
                return hmac.compare_digest(supplied.encode("utf-8"), ("Bearer " + owner.token).encode("utf-8"))

            def _send(self, status: int, body: dict):
                raw = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Connection", "close")
                if self._origin():
                    self.send_header("Access-Control-Allow-Origin", self._origin())
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                self.close_connection = True

            def do_OPTIONS(self):
                if not self._origin():
                    self._send(403, {"error": "Origin not allowed"})
                    return
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", self._origin())
                self.send_header("Access-Control-Allow-Methods", "GET, POST")
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
                self.send_header("Content-Length", "0")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True

            def do_GET(self):
                if not self._authorized():
                    self._send(401, {"error": "Pairing required"})
                elif self.path == "/v1/status":
                    owner.state.client_seen = time.monotonic()
                    self._send(200, owner.state.status())
                elif self.path.startswith("/v1/agent-permit/"):
                    self._send(200, owner.state.agent_permission(self.path.rsplit("/", 1)[-1]))
                else:
                    self._send(404, {"error": "Unknown endpoint"})

            def do_POST(self):
                if not self._authorized():
                    self._send(401, {"error": "Pairing required"})
                    return
                try:
                    self.connection.settimeout(2)
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= MAX_BODY:
                        self._send(413, {"error": "Payload too large"})
                        return
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict):
                        raise ValueError("Expected object")
                    if self.path == "/v1/browser":
                        owner.state.receive_browser(payload)
                    elif self.path == "/v1/control":
                        owner.state.queue_control(payload)
                        self._send(202, {"ok": True, "queued": True})
                        return
                    elif self.path == "/v1/agent":
                        owner.state.agent_heartbeat(payload)
                    else:
                        self._send(404, {"error": "Unknown endpoint"})
                        return
                    self._send(200, {"ok": True})
                except ControlConflict as error:
                    self._send(409, {"error": str(error)})
                except (ValueError, TypeError, KeyError, TimeoutError):
                    self._send(400, {"error": "Invalid event"})

        self.http = ThreadingHTTPServer(("127.0.0.1", credentials["port"]), Handler)
        self.http.daemon_threads = True
        self.port = self.http.server_port
        self.thread = threading.Thread(target=self.http.serve_forever, name="breadcrumbs-bridge", daemon=True)

    @property
    def address(self):
        return f"http://127.0.0.1:{self.port}"

    def start(self):
        self.thread.start()
        return self

    def close(self):
        self.state.stopping = True
        self.state.active = False
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)
