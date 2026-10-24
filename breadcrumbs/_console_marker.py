"""Private hidden helper for a selected coding agent's terminal binding.

Invoked as python -m breadcrumbs._console_marker PID BIRTH LEASE PORT. Credentials
are read from the local pairing file, never from command-line arguments.
This module does not alter any console on import.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import re
import stat
import time
from pathlib import Path
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .bridge import pairing_file
from .terminal import _kernel, _linux_tty, _proc_stat, discover_agents, process_identity


class MarkerProblem(RuntimeError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class MarkerClient:
    def __init__(self, lease: str, port: int):
        credentials = json.loads(pairing_file().read_text(encoding="utf-8"))
        token = credentials.get("token", "")
        if not re.fullmatch(r"[a-f0-9]{64}", token):
            raise ValueError("Invalid bridge credentials")
        self.lease = lease
        self.base = f"http://127.0.0.1:{port}"
        self.token = token
        self.opener = build_opener(ProxyHandler({}), _NoRedirect())

    def _request(self, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.base + path, data=body, headers=headers)
        with self.opener.open(request, timeout=0.75) as response:
            value = json.loads(response.read(4096))
        if not isinstance(value, dict):
            raise ValueError("Invalid bridge response")
        return value

    def permit(self) -> dict:
        return self._request("/v1/agent-permit/" + self.lease)

    def heartbeat(self, console_key: str = "", problem: str = "") -> None:
        self._request("/v1/agent", dict(lease=self.lease, console_key=console_key, problem=problem))


class WindowsConsoleMarker:
    def __init__(self, pid: int, birth: str, lease: str):
        from ctypes import wintypes as w

        self.pid, self.birth, self.lease = pid, birth, lease
        self.marker = "[breadcrumbs:" + lease + "]"
        self.kernel = _kernel()
        self.attached = False
        self.applied = False
        self.mutex = None
        self.mutex_held = False
        self.original = ""
        self.written = ""
        self.checked_at = 0.0
        self.ambiguous = False
        self.kernel.AttachConsole.argtypes = [w.DWORD]
        self.kernel.AttachConsole.restype = w.BOOL
        self.kernel.FreeConsole.restype = w.BOOL
        self.kernel.GetConsoleWindow.restype = w.HWND
        self.kernel.GetConsoleTitleW.argtypes = [w.LPWSTR, w.DWORD]
        self.kernel.GetConsoleTitleW.restype = w.DWORD
        self.kernel.SetConsoleTitleW.argtypes = [w.LPCWSTR]
        self.kernel.SetConsoleTitleW.restype = w.BOOL
        self.kernel.GetConsoleProcessList.argtypes = [ctypes.POINTER(w.DWORD), w.DWORD]
        self.kernel.GetConsoleProcessList.restype = w.DWORD
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, w.BOOL, w.LPCWSTR]
        self.kernel.CreateMutexW.restype = w.HANDLE
        self.kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        self.kernel.WaitForSingleObject.restype = w.DWORD
        self.kernel.ReleaseMutex.argtypes = [w.HANDLE]
        try:
            if process_identity(pid) != birth:
                raise MarkerProblem("Selected process identity changed.")
            # Only the helper entry point detaches its own inherited console;
            # the TUI never calls FreeConsole or attaches another console.
            if not self.kernel.AttachConsole(pid):
                raise MarkerProblem(f"This process has no attachable console, or access was denied (error {ctypes.get_last_error()}).")
            self.attached = True
            if process_identity(pid) != birth:
                raise MarkerProblem("Selected process identity changed.")
            handle = self.kernel.GetConsoleWindow()
            if not handle:
                raise MarkerProblem("Console identity is unavailable for this terminal.")
            self.console_key = f"win-console:{int(handle)}"
            self.mutex = self.kernel.CreateMutexW(None, False, f"Local\\BreadcrumbsConsoleMarker-{int(handle)}")
            if not self.mutex or self.kernel.WaitForSingleObject(self.mutex, 0) not in (0, 128):
                raise MarkerProblem("Another selected agent already owns this console marker.")
            self.mutex_held = True
        except BaseException:
            self.close()
            raise

    def _title(self) -> str:
        buffer = ctypes.create_unicode_buffer(32768)
        ctypes.set_last_error(0)
        count = self.kernel.GetConsoleTitleW(buffer, len(buffer))
        if count == 0 and ctypes.get_last_error():
            raise MarkerProblem("Console title is not readable.")
        return buffer.value

    def _check_shared_console(self) -> None:
        from ctypes import wintypes as w

        if time.monotonic() - self.checked_at < 2:
            if self.ambiguous:
                raise MarkerProblem("Multiple coding agents share this console; active agent is ambiguous.")
            return
        self.checked_at = time.monotonic()
        ids = (w.DWORD * 1024)()
        count = self.kernel.GetConsoleProcessList(ids, len(ids))
        if not count or count > len(ids):
            raise MarkerProblem("Console process membership is unavailable.")
        members = set(ids[:count])
        agents = discover_agents(members)
        self.ambiguous = len(agents) > 1
        if self.ambiguous:
            raise MarkerProblem("Multiple coding agents share this console; active agent is ambiguous.")

    def activate(self) -> None:
        if process_identity(self.pid) != self.birth:
            raise MarkerProblem("Selected process identity changed.")
        self._check_shared_console()
        title = self._title()
        other = [value for value in re.findall(r"\[breadcrumbs:([a-f0-9]{24})\]", title) if value != self.lease]
        if other:
            raise MarkerProblem("This console already contains another agent marker.")
        # Preserve title changes made by the CLI itself while stripping only
        # this helper's own marker on pause or exit.
        base = title.replace(self.marker, "").rstrip()
        if not self.applied or self.marker not in title:
            self.original = base
            self.written = (base[:32000] + " " + self.marker).strip()
            if not self.kernel.SetConsoleTitleW(self.written):
                raise MarkerProblem("This terminal does not accept console title markers.")
            self.applied = True

    def restore(self) -> None:
        if not self.attached or not self.applied:
            return
        try:
            title = self._title()
            if self.marker in title:
                restored = self.original if title == self.written else title.replace(self.marker, "").rstrip()
                self.kernel.SetConsoleTitleW(restored)
        finally:
            self.applied = False

    def close(self) -> None:
        try:
            self.restore()
        except (OSError, MarkerProblem):
            pass
        if self.mutex:
            if self.mutex_held:
                self.kernel.ReleaseMutex(self.mutex)
            self.kernel.CloseHandle(self.mutex)
            self.mutex = None
        if self.attached:
            self.kernel.FreeConsole()
            self.attached = False


def _xterm_ancestry(pid: int) -> bool:
    """Only a known xterm ancestry is allowed; tmux/screen need integration."""
    seen = set()
    for _ in range(64):
        if pid < 1 or pid in seen:
            return False
        seen.add(pid)
        try:
            directory = Path(f"/proc/{pid}")
            if directory.stat().st_uid != os.geteuid():
                return False
            name = (directory / "comm").read_text().strip().lower()
            if name.startswith(("tmux", "screen")):
                return False
            if name in ("xterm", "uxterm"):
                return True
            _state, pid, _tty, _start = _proc_stat((directory / "stat").read_text())
        except (OSError, ValueError, IndexError):
            return False
    return False


def _foreground_job(pid: int) -> bool:
    try:
        value = Path(f"/proc/{pid}/stat").read_text()
        fields = value[value.rfind(")") + 1:].split()
        group, foreground = int(fields[2]), int(fields[5])
        return group > 0 and group == foreground
    except (OSError, ValueError, IndexError):
        return False


class LinuxTTYMarker:
    def __init__(self, pid: int, birth: str, lease: str):
        self.pid, self.birth = pid, birth
        self.marker = ("[breadcrumbs:" + lease + "]").encode("ascii")
        self.descriptor = None
        self.applied = False
        self.checked_at = 0.0
        self.ambiguous = False
        if process_identity(pid) != birth:
            raise MarkerProblem("Selected process identity changed.")
        tty = _linux_tty(pid)
        if not tty or not re.fullmatch(r"/dev/(?:pts/\d+|tty\d+)", tty):
            raise MarkerProblem("The selected process has no accessible owned terminal.")
        if not _xterm_ancestry(pid):
            raise MarkerProblem("Safe title restoration is not verified for this Linux terminal; xterm is supported.")
        flags = os.O_WRONLY | os.O_NOCTTY | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(tty, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISCHR(metadata.st_mode) or metadata.st_uid != os.geteuid():
            os.close(descriptor)
            raise MarkerProblem("The terminal is not an owned character device.")
        self.descriptor = descriptor
        self.console_key = f"linux-tty:{os.major(metadata.st_rdev)}:{os.minor(metadata.st_rdev)}"

    def _write(self, sequence: bytes) -> None:
        if self.descriptor is None:
            return
        while sequence:
            count = os.write(self.descriptor, sequence)
            if count <= 0:
                raise MarkerProblem("Terminal title marker could not be written.")
            sequence = sequence[count:]

    def activate(self) -> None:
        if process_identity(self.pid) != self.birth:
            raise MarkerProblem("Selected process identity changed.")
        if not _foreground_job(self.pid):
            raise MarkerProblem("The selected agent is not the terminal's foreground job.")
        if time.monotonic() - self.checked_at >= 2:
            self.checked_at = time.monotonic()
            tty = _linux_tty(self.pid)
            siblings = [target for target in discover_agents() if tty and target.get("tty") == tty]
            self.ambiguous = len(siblings) > 1
        if self.ambiguous:
            raise MarkerProblem("Multiple coding agents share this terminal; active agent is ambiguous.")
        if not self.applied:
            self._write(b"\x1b[22;2t")  # xterm: push window title, without reading terminal input
            self.applied = True
        self._write(b"\x1b]2;" + self.marker + b"\x07")

    def restore(self) -> None:
        if self.applied:
            try:
                self._write(b"\x1b[23;2t")  # pop the saved window title
            finally:
                self.applied = False

    def close(self) -> None:
        try:
            self.restore()
        except (OSError, MarkerProblem):
            pass
        if self.descriptor is not None:
            os.close(self.descriptor)
            self.descriptor = None


def marker_for(pid: int, birth: str, lease: str):
    if platform.system() == "Windows":
        return WindowsConsoleMarker(pid, birth, lease)
    if platform.system() == "Linux":
        return LinuxTTYMarker(pid, birth, lease)
    raise MarkerProblem("Terminal process markers are unavailable on this platform.")


def run_marker(pid: int, birth: str, lease: str, client, factory=marker_for,
               identity=process_identity, sleep=time.sleep) -> None:
    marker = None
    try:
        while True:
            if identity(pid) != birth:
                client.heartbeat(problem="Selected process ended or its identity changed.")
                break
            permit = client.permit()
            if permit.get("stopping"):
                break
            problem = ""
            if permit.get("active") is True:
                try:
                    if marker is None:
                        marker = factory(pid, birth, lease)
                    marker.activate()
                except (MarkerProblem, OSError) as error:
                    if marker is not None:
                        marker.restore()
                    problem = str(error) if isinstance(error, MarkerProblem) else "Terminal marker is unavailable."
            elif marker is not None:
                marker.restore()
            client.heartbeat(console_key=marker.console_key if marker and marker.applied else "", problem=problem)
            sleep(0.4)
    except (OSError, ValueError):
        # Lost bridge/credentials: immediately restore rather than leave a live tag.
        pass
    finally:
        if marker is not None:
            marker.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Private Breadcrumbs console marker helper")
    parser.add_argument("pid", type=int)
    parser.add_argument("birth")
    parser.add_argument("lease")
    parser.add_argument("port", type=int)
    args = parser.parse_args()
    if args.pid < 1 or not 1 <= args.port <= 65535:
        return
    if not re.fullmatch(r"[a-z0-9:-]{1,120}", args.birth) or not re.fullmatch(r"[a-f0-9]{24}", args.lease):
        return
    try:
        if platform.system() == "Windows":
            # A Windows venv launcher may give its child a console despite the
            # outer CREATE_NO_WINDOW flag. Detach only this private helper.
            kernel = _kernel()
            kernel.FreeConsole()
        client = MarkerClient(args.lease, args.port)
        run_marker(args.pid, args.birth, args.lease, client)
    except (OSError, ValueError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
