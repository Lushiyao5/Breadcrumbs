import hashlib
import http.client
import json
import time
from types import SimpleNamespace

import pytest

from breadcrumbs.activity import Context, IntegratedSource, classify, window_title_keys
from breadcrumbs.bridge import BridgeServer, BridgeState
from breadcrumbs.config import Settings


def browser_event(**overrides):
    return dict(profile_id="profile", browser_instance_id="instance", sent_at=time.time(),
                focused=True, tab_id=1, window_id=1, domain="docs.python.org", title="Python docs",
                title_key=hashlib.sha256(b"python docs").hexdigest(), page_key="a" * 64,
                incognito=False, tabs=[], **overrides)


def event(**overrides):
    value = browser_event()
    value.update(overrides)
    return value


def request(server, method, path, payload=None, token="test-token", origin=None, raw=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=3)
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
    connection.request(method, path, body=raw if raw is not None else json.dumps(payload) if payload is not None else None,
                       headers=headers)
    response = connection.getresponse()
    result = response.status, json.loads(response.read() or b"{}")
    connection.close()
    return result


@pytest.fixture
def server():
    bridge = BridgeServer(0, token="test-token").start()
    try:
        yield bridge
    finally:
        bridge.close()
    assert not bridge.thread.is_alive()


def test_real_http_pairing_origin_validation_and_limits(server):
    assert server.http.server_address[0] == "127.0.0.1"
    assert request(server, "GET", "/v1/status", token="bad")[0] == 401
    assert request(server, "GET", "/v1/status", origin="https://evil.example")[0] == 401
    status, body = request(server, "GET", "/v1/status", origin="chrome-extension://" + "a" * 32)
    assert status == 200 and body["pairing"] and not body["active"]
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=3)
    connection.putrequest("POST", "/v1/browser")
    connection.putheader("Authorization", "Bearer test-token")
    connection.putheader("Content-Length", "65537")
    connection.endheaders()  # reject oversized header without waiting for the body
    response = connection.getresponse()
    assert response.status == 413
    response.read()
    connection.close()
    assert request(server, "POST", "/v1/browser", raw="[]")[0] == 400
    assert request(server, "POST", "/v1/browser", raw="{")[0] == 400
    assert request(server, "POST", "/v1/browser", event(sent_at=0))[0] == 400
    assert request(server, "POST", "/v1/browser", event(domain="bad/path"))[0] == 200  # paused: metadata discarded
    server.state.publish(True, True)
    assert request(server, "POST", "/v1/browser", event(domain="bad/path"))[0] == 400
    assert request(server, "POST", "/v1/browser", event())[0] == 200
    assert server.state.browser_records()[0]["domain"] == "docs.python.org"


def test_consent_inventory_title_redaction_and_pause_clear():
    state = BridgeState()
    state.receive_browser(event(url="https://private.example/token", tabs=[event()]))
    assert state.browser_records()[0]["domain"] == ""
    state.publish(False, False, inventory=True)
    state.receive_browser(event(tabs=[event()]))
    assert state.browser_records()[0]["title"] == ""
    assert state.browser_tabs()[0]["title"] == "Python docs"  # explicit inventory
    assert "private.example" not in repr(state.profiles)
    state.publish(True, False)
    assert state.browser_tabs() == []
    state.receive_browser(event())
    assert state.browser_records()[0]["title"] == ""
    assert state.browser_records()[0]["page_key"] == "a" * 64
    state.publish(False, False)
    assert not state.browser_records()[0]["focused"]
    assert not state.browser_records()[0]["domain"]
    state.receive_browser(event())
    assert not state.browser_records()[0]["domain"]


def test_integrated_browser_native_correlation_deviations_and_staleness():
    state = BridgeState()
    state.publish(True, False)
    state.receive_browser(event())
    class Desktop:
        current = Context("chrome.exe", title_keys=window_title_keys("Python docs - Google Chrome"))
        def sample(self): return self.current
    desktop = Desktop()
    source = IntegratedSource(Settings(activity_titles=False), SimpleNamespace(state=state), desktop)
    context = source.sample()
    assert context.domain == "docs.python.org" and context.precision == "tab" and not context.title
    assert context.page_key == "a" * 64
    desktop.current = Context("Code.exe", "Editor")
    assert source.sample().app == "Code.exe"  # actual app wins over browser heartbeat
    desktop.current = Context("chrome.exe", title_keys=window_title_keys("Unrelated - Google Chrome"))
    assert source.sample().precision == "window"
    desktop.current = Context("chrome.exe", title_keys=window_title_keys("Python docs - Google Chrome"))
    state.receive_browser(event(profile_id="another-profile"))
    assert source.sample().precision == "window"  # ambiguous profiles
    state.profiles.pop("another-profile")
    state.profiles["profile"]["received_at"] -= 46
    assert source.sample().precision == "window"  # no stale tab labels
    state.receive_browser(event(incognito=True, title="secret", domain="private.com"))
    assert source.sample().status == "excluded"
    assert not source.sample().title
    assert "secret" not in repr(state.profiles)


def test_exact_pages_and_verified_agents_do_not_broaden_browser_scope():
    page = {"page_key": "a" * 64}
    assert classify(Context("chrome.exe", page_key="a" * 64), ["chrome"], [], [page]) == "planned"
    assert classify(Context("chrome.exe", page_key="b" * 64), ["chrome"], [], [page]) == "unclassified"
    assert Context("chrome", page_key="a" * 64).key != Context("chrome", page_key="b" * 64).key
    assert classify(Context("codex", agent_id="verified"), [], [], [], [{"id": "verified"}]) == "planned"
    assert classify(Context("WindowsTerminal", title="codex"), [], [], [], [{"id": "verified"}]) == "unclassified"


def test_agent_leases_expire_and_shared_console_is_ambiguous():
    state = BridgeState()
    state.publish(True, False)
    lease = state.register_agent(dict(id="one", pid=123, birth="birth"))
    assert state.agent_permission(lease)["active"]
    state.agent_heartbeat(dict(lease=lease, console_key="console"))
    assert len(state.agent_records()) == 1
    other = state.register_agent(dict(id="two", pid=456, birth="birth"))
    state.agent_heartbeat(dict(lease=other, console_key="console"))
    assert state.agent_records() == []
    state.agents[other]["last_seen"] -= 5
    assert len(state.agent_records()) == 1
    state.publish(False, False)
    assert not state.agent_permission(lease)["active"]


def test_out_of_order_browser_events_cannot_restore_old_tab():
    state = BridgeState()
    state.publish(True, True)
    newer = time.time()
    state.receive_browser(event(sent_at=newer, domain="new.example"))
    state.receive_browser(event(sent_at=newer - 1, domain="old.example"))
    assert state.browser_records()[0]["domain"] == "new.example"


def test_control_http_endpoint_requires_pairing_and_rejects_stale_commands(server):
    server.state.publish_timer(dict(status="ready", session_id=None, name="test", kind="focus",
                                    remaining_seconds=1500, can_control=True, ui_theme="midnight"))
    timer = server.state.status()["timer"]
    payload = dict(action="start", session_id=None, revision=timer["revision"])
    assert request(server, "POST", "/v1/control", payload, token="wrong")[0] == 401
    assert request(server, "POST", "/v1/control", payload, origin="https://example.com")[0] == 401
    assert request(server, "POST", "/v1/control", dict(payload, revision=-1))[0] == 409
    assert request(server, "POST", "/v1/control", payload)[0] == 202
    assert request(server, "POST", "/v1/control", payload)[0] == 409
    assert server.state.take_controls()[0]["action"] == "start"


def test_agent_attribution_requires_foreground_marker_live_lease_and_birth(monkeypatch):
    state = BridgeState()
    state.publish(True, False)
    target = dict(id="codex:123:birth", kind="codex", pid=123, birth="birth", label="Codex")
    lease = state.register_agent(target)
    state.agent_heartbeat(dict(lease=lease, console_key="test-console"))
    class Desktop:
        context = Context("WindowsTerminal.exe", title="Generic terminal", markers=(lease,))
        def sample(self): return self.context
    desktop = Desktop()
    monkeypatch.setattr("breadcrumbs.terminal.process_identity", lambda pid: "birth")
    source = IntegratedSource(Settings(), SimpleNamespace(state=state), desktop)
    assert source.sample().agent_id == target["id"]
    assert source.sample().precision == "terminal-marker"
    desktop.context = Context("WindowsTerminal.exe", title="Codex running somewhere")
    assert source.sample().agent_id == ""
    desktop.context = Context("WindowsTerminal.exe", markers=(lease,))
    monkeypatch.setattr("breadcrumbs.terminal.process_identity", lambda pid: "reused-pid-birth")
    assert source.sample().agent_id == ""
    monkeypatch.setattr("breadcrumbs.terminal.process_identity", lambda pid: "birth")
    state.agents[lease]["enabled"] = False
    assert source.sample().agent_id == ""


def test_selected_url_with_window_only_capture_is_unknown_until_verified():
    state = BridgeState()
    state.publish(True, True)
    class Desktop:
        def sample(self):
            return Context("chrome.exe", "Python docs - Google Chrome",
                           title_keys=window_title_keys("Python docs - Google Chrome"))
    settings = Settings(activity_source="integrated", activity_pages=[{"page_key": "a" * 64}])
    source = IntegratedSource(settings, SimpleNamespace(state=state), Desktop())
    assert source.sample().status == "unknown"
    state.receive_browser(event())
    context = source.sample()
    assert classify(context, ["chrome"], [], settings.activity_pages) == "planned"
    state.receive_browser(event(page_key="b" * 64))
    assert classify(source.sample(), ["chrome"], [], settings.activity_pages) == "unclassified"
    state.receive_browser(event())
    assert classify(source.sample(), ["chrome"], [], settings.activity_pages) == "planned"


def test_selected_agent_without_marker_reports_verification_problem():
    target = dict(id="codex:123:birth", kind="codex", pid=123, birth="birth", label="Codex")
    state = BridgeState()
    state.publish(True, False)
    lease = state.register_agent(target)
    state.agent_heartbeat(dict(lease=lease, console_key="", problem="No attachable console"))
    class Desktop:
        def sample(self): return Context("WindowsTerminal.exe")
    settings = Settings(activity_agents=[target])
    source = IntegratedSource(settings, SimpleNamespace(state=state), Desktop())
    assert source.sample().status == "unknown" and "attachable" in source.sample().notice
    settings.activity_apps = ["WindowsTerminal"]
    assert source.sample().status == "active"


def test_browser_ipv6_literals_are_normalized_without_accepting_urls():
    state = BridgeState()
    state.publish(True, False)
    state.receive_browser(event(domain="[::1]"))
    assert state.browser_records()[0]["domain"] == "::1"
    state.receive_browser(event(domain="[2001:0db8:0:0:0:0:0:1]"))
    assert state.browser_records()[0]["domain"] == "2001:db8::1"
    with pytest.raises(ValueError):
        state.receive_browser(event(domain="http://[::1]/private"))


def test_browser_window_fallback_never_persists_unverified_private_titles():
    class Desktop:
        def sample(self): return Context("chrome.exe", title="Private browsing fixture")
    source = IntegratedSource(Settings(activity_titles=True), None, Desktop())
    assert source.sample().title == ""


def test_old_extension_reports_are_identified_in_status_and_missing_tab_notice():
    state = BridgeState()
    state.publish(True, True)
    state.receive_browser(event())
    assert state.status()["browser_diagnostics"]["versions"] == ["unreported"]
    class Desktop:
        def sample(self): return Context("chrome.exe", title_keys=window_title_keys("Another page - Google Chrome"))
    source = IntegratedSource(Settings(activity_domains=["python.org"]), SimpleNamespace(state=state), Desktop())
    assert "old browser extension" in source.sample().notice
    from breadcrumbs import __version__
    state.receive_browser(event(extension_version=__version__))
    assert state.status()["browser_diagnostics"]["versions"] == [__version__]
    assert "old browser extension" not in source.sample().notice


@pytest.mark.parametrize("window_title", ["Python docs — Google Chrome", "Python docs – Microsoft Edge",
    "Python docs | Brave", "Python docs - Google Chrome - Work profile", "Python docs — Mozilla Firefox"])
def test_browser_title_variants_correlate_the_actual_reported_tab(window_title):
    state = BridgeState()
    state.publish(True, True)
    state.receive_browser(event())
    class Desktop:
        def sample(self):
            return Context("chrome.exe", title_keys=window_title_keys(window_title))
    source = IntegratedSource(Settings(), SimpleNamespace(state=state), Desktop())
    context = source.sample()
    assert context.title == "Python docs" and context.domain == "docs.python.org"
    assert context.precision == "tab"
    state.receive_browser(event(profile_id="other-profile"))
    assert source.sample().precision == "window"  # still no guessing across ambiguous profiles
