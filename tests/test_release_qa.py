"""Release security and concurrency checks using synthetic loopback clients only."""
from concurrent.futures import ThreadPoolExecutor
import http.client
import json

import pytest

from breadcrumbs.bridge import BridgeServer

TOKEN = "release-qa-token"
EXTENSION = "chrome-extension://" + "a" * 32


@pytest.fixture
def bridge():
    server = BridgeServer(0, token=TOKEN).start()
    try:
        yield server
    finally:
        server.close()


def exchange(server, method, path="/v1/status", payload=None, origin=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=3)
    headers = {"Authorization": "Bearer " + TOKEN}
    if origin is not None:
        headers["Origin"] = origin
    body = None if payload is None else json.dumps(payload)
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def publish_running(server, session_id=41):
    server.state.publish_timer(dict(status="running", session_id=session_id, name="synthetic-qa",
                                   remaining_seconds=90, kind="focus", can_control=True,
                                   ui_theme="midnight"))
    return server.state.status()["timer"]


@pytest.mark.parametrize("origin", ["https://evil.example", "null", "chrome-extension://" + "z" * 32,
                                    EXTENSION + ".evil", "http://127.0.0.1:9999"])
def test_valid_token_does_not_authorize_untrusted_web_origins(bridge, origin):
    timer = publish_running(bridge)
    command = dict(action="finish", session_id=41, revision=timer["revision"])
    assert exchange(bridge, "GET", origin=origin)[0] == 401
    assert exchange(bridge, "POST", "/v1/control", command, origin)[0] == 401
    assert bridge.state.take_controls() == []
    code, headers, _ = exchange(bridge, "OPTIONS", origin=origin)
    assert code == 403
    assert "Access-Control-Allow-Origin" not in headers


def test_extension_origin_receives_cors_only_for_its_exact_origin(bridge):
    code, headers, body = exchange(bridge, "GET", origin=EXTENSION)
    assert code == 200 and json.loads(body)["pairing"] is True
    assert headers["Access-Control-Allow-Origin"] == EXTENSION
    assert exchange(bridge, "OPTIONS", origin=EXTENSION)[0] == 204


def test_concurrent_duplicate_finish_accepts_exactly_one_command(bridge):
    timer = publish_running(bridge)
    payload = dict(action="finish", session_id=41, revision=timer["revision"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: exchange(bridge, "POST", "/v1/control", payload)[0], range(2)))
    assert sorted(results) == [202, 409]
    assert bridge.state.take_controls() == [dict(action="finish", session_id=41, status="running")]


def test_delayed_finish_cannot_target_a_later_session(bridge):
    old = publish_running(bridge)
    publish_running(bridge, session_id=42)
    payload = dict(action="finish", session_id=41, revision=old["revision"])
    assert exchange(bridge, "POST", "/v1/control", payload)[0] == 409
    assert bridge.state.take_controls() == []
    assert bridge.state.status()["timer"]["session_id"] == 42
