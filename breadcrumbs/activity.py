"""Opt-in activity sources. No collection happens on import or in off mode."""

from __future__ import annotations

import ctypes
import hashlib
import json
import ntpath
import os
import platform
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from urllib.parse import urlsplit


def clean(value: object, limit: int = 240) -> str:
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(value or ""))[:limit].strip()


def app_key(app: str) -> str:
    return ntpath.basename(app).lower().removesuffix(".exe").strip()


def domain_name(value: str) -> str:
    parsed = urlsplit(value if "://" in value else "https://" + value)
    if parsed.scheme not in ("http", "https"):
        return ""
    return (parsed.hostname or "").lower().removeprefix("www.").rstrip(".")


def is_browser(app: str) -> bool:
    return any(part in app_key(app) for part in ("chrome", "chromium", "firefox", "brave", "msedge", "edge", "vivaldi", "opera", "safari"))


def activity_label(value: str) -> str:
    """Readable UI names; durable observation codes stay compatible with exports."""
    return {"planned": "In scope", "unclassified": "Deviation", "supporting": "Supporting",
            "away": "Away", "unknown": "Unknown", "excluded": "Excluded",
            "break": "Break", "block": "Work block"}.get(value, value)


@dataclass(frozen=True)
class Context:
    app: str
    title: str = ""
    domain: str = ""
    identity: str = ""
    source: str = "desktop"
    precision: str = "window"
    status: str = "active"
    notice: str = ""
    title_keys: tuple[str, ...] = ()
    markers: tuple[str, ...] = ()
    page_key: str = ""
    agent_id: str = ""
    host_app: str = ""

    @property
    def key(self) -> str:
        return hashlib.sha256(
            json.dumps((self.app, self.title, self.domain, self.identity, self.source, self.status,
                        self.page_key, self.agent_id)).encode()
        ).hexdigest()


def classify(context: Context, apps: list[str], domains: list[str],
             pages: list[dict] | None = None, agents: list[dict] | None = None) -> str:
    if context.status != "active":
        return context.status
    if context.agent_id and any(agent.get("id") == context.agent_id for agent in agents or []):
        return "planned"
    if is_browser(context.app) and (domains or pages):
        if not context.domain and not context.page_key:
            return "unknown"  # Window-only capture cannot establish a page deviation.
        if context.page_key and any(page.get("page_key") == context.page_key for page in pages or []):
            return "planned"
        return "planned" if any(
            context.domain == rule or context.domain.endswith("." + rule)
            for rule in domains if rule
        ) else "unclassified"
    planned = {app_key(app) for app in apps}
    return "planned" if app_key(context.app) in planned or app_key(context.host_app) in planned else "unclassified"


def window_title_keys(title: str) -> tuple[str, ...]:
    title = title.strip().lower()
    variants = {title}
    suffixes = (" - google chrome", " - chromium", " - brave", " - microsoft edge",
                " — mozilla firefox", " - mozilla firefox", " - vivaldi", " - opera")
    for suffix in suffixes:
        if title.endswith(suffix):
            variants.add(title[:-len(suffix)].strip())
    # Browser chrome uses different dash glyphs and may append a profile name.
    # Strip only a known browser suffix; arbitrary title fragments are not matches.
    browser_suffix = re.search(
        r"\s+[-—–|]\s+(?:google chrome|chromium|brave|microsoft edge|mozilla firefox|vivaldi|opera)"
        r"(?:\s+[-—–|]\s+[^\r\n]{1,100})?$", title,
    )
    if browser_suffix:
        variants.add(title[:browser_suffix.start()].strip())
    return tuple(hashlib.sha256(value.encode()).hexdigest() for value in variants if value)


def title_markers(title: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\[breadcrumbs:([a-f0-9]{24})\]", title))


class UnavailableSource:
    def __init__(self, message: str):
        self.message = message

    def sample(self) -> Context:
        return Context("Unknown", status="unknown", notice=self.message)


class WindowsSource:
    def __init__(self, titles: bool = True):
        from ctypes import wintypes as w

        self.titles = titles
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user.GetForegroundWindow.restype = w.HWND
        self.user.GetWindowTextLengthW.argtypes = [w.HWND]
        self.user.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
        self.user.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
        self.kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.kernel.OpenProcess.restype = w.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.GetTickCount.restype = w.DWORD
        self.user.IsWindowVisible.argtypes = [w.HWND]
        self._callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        self.user.EnumWindows.argtypes = [self._callback_type, w.LPARAM]

    def _window(self, hwnd) -> tuple[str, str, str]:
        from ctypes import wintypes as w

        pid = w.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        title = ctypes.create_unicode_buffer(min(4096, self.user.GetWindowTextLengthW(hwnd) + 1))
        self.user.GetWindowTextW(hwnd, title, len(title))
        handle = self.kernel.OpenProcess(0x1000, False, pid.value)
        app = "Unknown app"
        if handle:
            try:
                length = w.DWORD(32768)
                buffer = ctypes.create_unicode_buffer(length.value)
                if self.kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
                    app = ntpath.basename(buffer.value)
            finally:
                self.kernel.CloseHandle(handle)
        return clean(app), clean(title.value, 4096), f"{pid.value}:{int(hwnd)}"

    def sample(self) -> Context:
        from ctypes import wintypes as w

        class LastInput(ctypes.Structure):
            _fields_ = [("cbSize", w.UINT), ("dwTime", w.DWORD)]

        info = LastInput()
        info.cbSize = ctypes.sizeof(info)
        if self.user.GetLastInputInfo(ctypes.byref(info)):
            idle_ms = (self.kernel.GetTickCount() - info.dwTime) & 0xFFFFFFFF
            if idle_ms >= 180_000:
                return Context("Away", status="away", notice="No input for 3 minutes")
        hwnd = self.user.GetForegroundWindow()
        if not hwnd:
            return Context("Unknown", status="unknown", notice="No foreground window")
        app, title, identity = self._window(hwnd)
        if app == "Unknown app":
            return Context("Unknown app", status="unknown", notice="Window owner unavailable or inaccessible")
        return Context(app, clean(title) if self.titles else "", identity=identity,
                       notice="Desktop window", title_keys=window_title_keys(title), markers=title_markers(title))

    def candidates(self) -> list[str]:
        names = set()

        def visit(hwnd, _):
            if self.user.IsWindowVisible(hwnd):
                app, title, _ = self._window(hwnd)
                if title and app != "Unknown app":
                    names.add(app)
            return True

        self.user.EnumWindows(self._callback_type(visit), 0)
        return sorted(names, key=str.lower)


class X11Source:
    def __init__(self, titles: bool = True):
        self.titles = titles

    @staticmethod
    def _run(*args: str) -> str:
        return subprocess.run(args, capture_output=True, text=True, timeout=0.7, check=True).stdout

    def sample(self) -> Context:
        active = self._run("xprop", "-root", "_NET_ACTIVE_WINDOW")
        match = re.search(r"0x[0-9a-fA-F]+", active)
        if not match or match[0] == "0x0":
            return Context("Unknown", status="unknown", notice="No foreground X11 window")
        window = match[0]
        props = self._run("xprop", "-id", window, "WM_CLASS", "_NET_WM_NAME")
        app = "Unknown app"
        title = ""
        for line in props.splitlines():
            quoted = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
            if line.startswith("WM_CLASS") and quoted:
                app = quoted[-1]
            elif line.startswith("_NET_WM_NAME") and quoted:
                title = quoted[0]
        return Context(clean(app), clean(title) if self.titles else "", identity=window,
                       source="x11", notice="X11 window · idle signal unavailable",
                       title_keys=window_title_keys(title), markers=title_markers(title))




def native_source(settings):
    if platform.system() == "Windows":
        return WindowsSource(settings.activity_titles)
    if os.environ.get("XDG_SESSION_TYPE") == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
        return UnavailableSource("Wayland compositor capture unavailable")
    if platform.system() == "Linux" and os.environ.get("DISPLAY") and shutil.which("xprop"):
        return X11Source(settings.activity_titles)
    return UnavailableSource("Native desktop capture unavailable")


class IntegratedSource:
    def __init__(self, settings, bridge, desktop=None):
        self.settings = settings
        self.bridge = bridge
        self.desktop = desktop or native_source(settings)

    def sample(self) -> Context:
        native = self.desktop.sample()
        if native.status in ("away", "excluded"):
            return native
        state = self.bridge.state if self.bridge else None
        if state is not None:
            from .terminal import is_terminal, process_identity
            if is_terminal(native.app):
                verified_agents = state.agent_records()
                for agent in verified_agents:
                    if agent["lease"] in native.markers and process_identity(agent["pid"]) == agent["birth"]:
                        return Context(
                            agent["kind"], clean(agent.get("label", agent["kind"])) if self.settings.activity_titles else "",
                            identity=agent["id"], source="suite", precision="terminal-marker",
                            notice="Verified process + active terminal title marker", agent_id=agent["id"],
                            host_app=native.app,
                        )
                selected = self.settings.activity_agents
                selected_ids = {agent.get("id") for agent in selected}
                host_selected = app_key(native.app) in {app_key(app) for app in self.settings.activity_apps}
                if selected and not host_selected and not any(agent["id"] in selected_ids for agent in verified_agents):
                    problem = state.agent_problem(selected_ids)
                    return Context(native.app, native.title, identity=native.identity, source=native.source,
                                   status="unknown", precision="window",
                                   notice=problem or "Selected agent not verified · B → Scope / source")
            records = [record for record in state.browser_records() if record["focused"]]
            if native.status == "active" and not is_browser(native.app):
                return native  # a browser heartbeat never hides a deviation to another app
            eligible = records if native.status == "unknown" else [
                record for record in records if record["incognito"] or record["title_key"] in native.title_keys
            ]
            if len(eligible) == 1:
                tab = eligible[0]
                if tab["incognito"]:
                    return Context("Private browsing", source="suite", status="excluded", notice="Private tab excluded")
                if tab["domain"]:
                    identity = f"{tab['profile_id']}:{tab['browser_instance_id']}:{tab['window_id']}:{tab['tab_id']}"
                    return Context(
                        native.app if is_browser(native.app) else "chrome", tab["title"] if self.settings.activity_titles else "",
                        tab["domain"], identity=identity, source="suite",
                        precision="tab" if native.status == "active" else "browser-focus",
                        notice="Bundled browser bridge" if native.status == "active" else "Browser focus · desktop source unavailable",
                        page_key=tab["page_key"],
                    )
        if native.status == "active" and is_browser(native.app):
            narrowed = bool(self.settings.activity_pages or self.settings.activity_domains)
            if state is None or not state.browser_records():
                problem = "No recent browser reports · open the extension and check pairing/sharing"
            elif not any(record["focused"] for record in state.browser_records()):
                problem = "No focused web tab reported · check extension sharing and page permissions"
            else:
                problem = "Browser window/tab match is ambiguous · check the active browser profile"
            if state is not None and any(not record.get("extension_version") for record in state.browser_records()):
                problem = "An old browser extension is still reporting · Reload Breadcrumbs in chrome://extensions"
            return Context(native.app, "", identity=native.identity, source=native.source,
                           status="unknown" if narrowed else "active",
                           notice=problem, precision="window")
        return native


def create_source(settings, bridge=None):
    if settings.activity_source in ("integrated", "activitywatch"):
        return IntegratedSource(settings, bridge)
    if settings.activity_source != "desktop":
        return UnavailableSource("Tracking is off")
    return native_source(settings)


def suggested_apps() -> list[str]:
    """Called only when the user explicitly opens the scope picker."""
    if platform.system() == "Windows":
        try:
            apps = WindowsSource(False).candidates()
            if apps:
                return apps
        except (OSError, AttributeError):
            pass
    if platform.system() == "Linux" and shutil.which("wmctrl"):
        try:
            output = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True, timeout=1, check=True).stdout
            apps = sorted({line.split()[2].rsplit(".", 1)[-1] for line in output.splitlines() if len(line.split()) >= 3})
            if apps:
                return apps
        except (OSError, subprocess.SubprocessError):
            pass
    if platform.system() == "Windows":
        return ["Code.exe", "chrome.exe", "msedge.exe", "Spotify.exe", "WindowsTerminal.exe", "claude", "codex"]
    return ["code", "chromium", "firefox", "spotify", "claude", "codex", "terminal"]
