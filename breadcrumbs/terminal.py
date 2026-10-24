"""Selected coding-agent discovery and lifetime-managed terminal marker helpers.

Discovery is a list of candidates, not evidence of attention. Activity becomes
agent-specific only when a live, birth-verified process has a current marker in
the foreground terminal title. No helper is started on import.
"""

from __future__ import annotations

import ctypes
import json
import ntpath
import os
import platform
import re
import struct
import subprocess
import sys
import time
from pathlib import Path


_TERMINALS = {
    "windowsterminal", "windowsterminalpreview", "windows terminal", "conhost",
    "openconsole", "powershell", "pwsh", "cmd", "wezterm", "wezterm-gui",
    "alacritty", "kitty", "gnome-terminal", "gnome-terminal-server",
    "org.gnome.terminal", "konsole", "xterm", "uxterm", "rxvt", "urxvt",
    "tilix", "xfce4-terminal", "mate-terminal", "lxterminal", "terminator", "st",
}


def is_terminal(app: str) -> bool:
    name = ntpath.basename(str(app or "")).lower().removesuffix(".exe").removesuffix(".desktop")
    return name in _TERMINALS


def terminal_hint(app: str, title: str) -> str | None:
    """Display-only hint from an explicit foreground terminal title.

    This never supplies agent_id or changes scope classification. A process
    running elsewhere and prose mentioning a tool are not foreground evidence.
    """
    if not is_terminal(app) or not title:
        return None
    title = re.sub(r"\[breadcrumbs:[a-f0-9]{24}\]", "", title).strip()
    title = title.lstrip("✳✻✽✶✢⠂⠐●○ ")
    patterns = (("claude_code", r"claude(?:[ -]code)?"), ("codex", r"codex"),
                ("neovim", r"(?:neovim|nvim)"), ("python", r"python(?:3(?:\.\d+)?)?"),
                ("nodejs", r"node(?:\.js)?"), ("git", r"git"))
    for key, pattern in patterns:
        if re.match(r"^(?:" + pattern + r")(?:$|\s*[:|—–-]\s*|\s+v?\d)", title, re.IGNORECASE):
            return key
    return None


def _proc_stat(value: str) -> tuple[str, int, int, str]:
    """Parse after the final ')' because Linux comm can itself contain ')'."""
    close = value.rfind(")")
    if close < 0:
        raise ValueError("Invalid process stat")
    fields = value[close + 1:].split()
    return fields[0], int(fields[1]), int(fields[4]), fields[19]


def _kernel():
    from ctypes import wintypes as w

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.GetProcessTimes.argtypes = [w.HANDLE] + [ctypes.POINTER(w.FILETIME)] * 4
    kernel.GetProcessTimes.restype = w.BOOL
    kernel.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
    kernel.GetExitCodeProcess.restype = w.BOOL
    kernel.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = w.BOOL
    kernel.ProcessIdToSessionId.argtypes = [w.DWORD, ctypes.POINTER(w.DWORD)]
    kernel.ProcessIdToSessionId.restype = w.BOOL
    return kernel


def process_identity(pid: int) -> str | None:
    """Stable process birth identity; None means unavailable, exited, or invalid."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
        return None
    try:
        if platform.system() == "Windows":
            from ctypes import wintypes as w

            kernel = _kernel()
            handle = kernel.OpenProcess(0x1000, False, pid)
            if not handle:
                return None
            try:
                creation, exit_time, kernel_time, user_time = (w.FILETIME() for _ in range(4))
                code = w.DWORD()
                if not kernel.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time),
                                              ctypes.byref(kernel_time), ctypes.byref(user_time)):
                    return None
                if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
                    return None
                return f"win:{(creation.dwHighDateTime << 32) | creation.dwLowDateTime}"
            finally:
                kernel.CloseHandle(handle)
        if platform.system() == "Linux":
            state, _parent, _tty, start = _proc_stat(Path(f"/proc/{pid}/stat").read_text())
            if state in ("Z", "X", "x"):
                return None
            boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            if not re.fullmatch(r"[a-f0-9-]{36}", boot):
                return None
            return f"linux:{boot}:{start}"
    except (OSError, ValueError, IndexError, AttributeError):
        return None
    return None


def _agent_kind(name: str, argv: list[str] | None = None) -> str | None:
    name = ntpath.basename(name).lower().removesuffix(".exe")
    if name in ("claude", "claude-code"):
        return "claude-code"
    if name == "codex":
        return "codex"
    if name not in ("node", "nodejs") or not argv or len(argv) < 2:
        return None
    script = argv[1].replace("\\", "/").lower()
    if re.search(r"(?:^|/)@anthropic-ai/claude-code/(?:cli|index)\.js$", script):
        return "claude-code"
    if re.search(r"(?:^|/)@openai/codex/bin/codex\.js$", script):
        return "codex"
    return None


def _linux_tty(pid: int) -> str | None:
    for descriptor in (0, 1, 2):
        try:
            path = os.readlink(f"/proc/{pid}/fd/{descriptor}")
            if path.startswith("/dev/pts/") or re.fullmatch(r"/dev/tty\d+", path):
                if os.stat(path).st_uid == os.geteuid():
                    return path
        except OSError:
            pass
    return None


def _linux_processes(pids: set[int] | None = None):
    for directory in Path("/proc").iterdir():
        if not directory.name.isdigit():
            continue
        if pids is not None and int(directory.name) not in pids:
            continue
        try:
            if directory.stat().st_uid != os.geteuid():
                continue
            pid = int(directory.name)
            birth = process_identity(pid)
            if birth is None:
                continue
            _state, parent, _tty, _start = _proc_stat((directory / "stat").read_text())
            name = (directory / "comm").read_text().strip()
            argv = None
            if name in ("node", "nodejs"):
                with (directory / "cmdline").open("rb") as stream:
                    # The launch-script argument is enough; commands/prompts are
                    # never returned, labeled, logged, or retained.
                    argv = [part.decode("utf-8", "replace") for part in stream.read(8192).split(b"\0")[:2]]
            yield dict(pid=pid, parent=parent, name=name, argv=argv, birth=birth,
                       owned=True, console=True, tty=_linux_tty(pid))
        except (OSError, ValueError, IndexError):
            continue


def _console_executable(path: str) -> bool:
    """Exclude Electron/desktop Claude and Codex GUI apps from CLI candidates."""
    try:
        with open(path, "rb") as stream:
            header = stream.read(64)
            if header[:2] != b"MZ" or len(header) < 64:
                return False
            offset = struct.unpack_from("<I", header, 60)[0]
            if offset > 1_048_576:
                return False
            stream.seek(offset)
            pe = stream.read(96)
            return pe[:4] == b"PE\0\0" and struct.unpack_from("<H", pe, 92)[0] == 3
    except (OSError, struct.error):
        return False


def _windows_node_argv(pids: list[int]) -> dict[int, list[str]]:
    if not pids:
        return {}
    # CIM is only a fallback for npm's node launcher. Native agent executables
    # need no shell/process-command-line inspection.
    script = (
        "$wanted=@(" + ",".join(str(pid) for pid in pids[:128]) + "); "
        "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | "
        "Where-Object { $_.ProcessId -in $wanted } | "
        "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=2, check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        values = json.loads(result.stdout or "[]")
        if isinstance(values, dict):
            values = [values]
        from ctypes import wintypes as w

        shell = ctypes.WinDLL("shell32", use_last_error=True)
        shell.CommandLineToArgvW.argtypes = [w.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
        shell.CommandLineToArgvW.restype = ctypes.POINTER(w.LPWSTR)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.LocalFree.argtypes = [w.HLOCAL]
        commands = {}
        for row in values:
            if not isinstance(row, dict):
                continue
            count = ctypes.c_int()
            pointers = shell.CommandLineToArgvW(str(row.get("CommandLine") or ""), ctypes.byref(count))
            if pointers:
                try:
                    commands[int(row["ProcessId"])] = [pointers[index] for index in range(min(count.value, 2))]
                finally:
                    kernel.LocalFree(pointers)
        return commands
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return {}


def _windows_processes(pids: set[int] | None = None):
    from ctypes import wintypes as w

    class Entry(ctypes.Structure):
        _fields_ = [
            ("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", w.DWORD),
            ("cntThreads", w.DWORD), ("th32ParentProcessID", w.DWORD),
            ("pcPriClassBase", w.LONG), ("dwFlags", w.DWORD), ("szExeFile", w.WCHAR * 260),
        ]

    kernel = _kernel()
    kernel.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = w.HANDLE
    kernel.Process32FirstW.argtypes = [w.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [w.HANDLE, ctypes.POINTER(Entry)]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot in (None, ctypes.c_void_p(-1).value):
        return
    current_session = w.DWORD()
    if not kernel.ProcessIdToSessionId(os.getpid(), ctypes.byref(current_session)):
        kernel.CloseHandle(snapshot)
        return
    candidates = []
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(entry)
        success = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while success:
            name = entry.szExeFile
            if (pids is None or entry.th32ProcessID in pids) and name.lower() in ("claude.exe", "claude-code.exe", "codex.exe", "node.exe"):
                session = w.DWORD()
                pid = entry.th32ProcessID
                if kernel.ProcessIdToSessionId(pid, ctypes.byref(session)) and session.value == current_session.value:
                    handle = kernel.OpenProcess(0x1000, False, pid)
                    if handle:
                        try:
                            length = w.DWORD(32768)
                            buffer = ctypes.create_unicode_buffer(length.value)
                            if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)) and _console_executable(buffer.value):
                                candidates.append(dict(pid=pid, parent=entry.th32ParentProcessID,
                                                       name=name, owned=True, console=True,
                                                       birth=process_identity(pid)))
                        finally:
                            kernel.CloseHandle(handle)
            success = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    commands = _windows_node_argv([row["pid"] for row in candidates if row["name"].lower() == "node.exe"])
    for row in candidates:
        row["argv"] = commands.get(row["pid"])
        yield row


def _iter_processes(pids: set[int] | None = None):
    if platform.system() == "Windows":
        yield from _windows_processes(pids)
    elif platform.system() == "Linux":
        yield from _linux_processes(pids)


def discover_agents(pids: set[int] | None = None) -> list[dict]:
    """Return live CLI candidates, never an inference that an agent has focus."""
    found = []
    try:
        for row in _iter_processes(pids):
            kind = _agent_kind(row.get("name", ""), row.get("argv"))
            if not kind or not row.get("owned") or not row.get("console"):
                continue
            pid, birth = row["pid"], row.get("birth")
            if not birth or process_identity(pid) != birth:
                continue
            target = dict(id=f"{kind}:{pid}:{birth}", kind=kind, pid=pid, birth=birth,
                          label=f"{'Claude Code' if kind == 'claude-code' else 'Codex'} · PID {pid}")
            if row.get("tty"):
                target["tty"] = row["tty"]
            found.append((target, row.get("parent")))
    except (OSError, ValueError, TypeError):
        return []
    # npm's launcher plus its same-kind native child are one candidate. Prefer
    # the leaf process that actually owns the interactive agent.
    parents = {(parent, target["kind"]) for target, parent in found}
    return sorted([target for target, _ in found if (target["pid"], target["kind"]) not in parents],
                  key=lambda target: (target["kind"], target["pid"]))


class AgentMarkers:
    """Own only the hidden marker helpers created for this TUI's selected agents."""

    def __init__(self, bridge):
        self.bridge = bridge
        self.helpers: dict[str, dict] = {}
        self.retired: list[dict] = []

    def _disable(self, record: dict) -> None:
        with self.bridge.state.lock:
            agent = self.bridge.state.agents.get(record["lease"])
            if agent:
                agent["enabled"] = False

    def sync(self, targets: list[dict]) -> None:
        if self.bridge is None:
            return
        wanted = {target.get("id"): target for target in targets if isinstance(target, dict) and target.get("id")}
        for identifier, record in list(self.helpers.items()):
            target = wanted.get(identifier)
            if target is None or target.get("birth") != record["target"].get("birth"):
                self._disable(record)
                self.helpers.pop(identifier)
                self.retired.append(record)
        self.retired = [
            record for record in self.retired
            if record["process"] is not None and record["process"].poll() is None
        ]
        for identifier, target in wanted.items():
            if identifier in self.helpers:
                continue
            if target.get("kind") not in ("claude", "claude-code", "codex"):
                continue
            if not isinstance(target.get("pid"), int) or process_identity(target["pid"]) != target.get("birth"):
                continue
            safe = {key: target[key] for key in ("id", "kind", "pid", "birth", "label") if key in target}
            if target.get("tty"):
                safe["tty"] = target["tty"]
            lease = self.bridge.state.register_agent(safe)
            record = dict(target=safe, lease=lease, process=None)
            self.helpers[identifier] = record
            try:
                command = [sys.executable, "-m", "breadcrumbs._console_marker",
                           str(safe["pid"]), safe["birth"], lease, str(self.bridge.port)]
                options = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if platform.system() == "Windows":
                    options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                else:
                    options["start_new_session"] = True
                record["process"] = subprocess.Popen(command, **options)
            except OSError:
                self.bridge.state.agent_heartbeat(dict(lease=lease, console_key="", problem="Could not start the terminal marker helper."))

    def close(self) -> None:
        if self.bridge is None:
            return
        records = list(self.helpers.values()) + self.retired
        for record in records:
            self._disable(record)
        deadline = time.monotonic() + 3
        for record in records:
            process = record["process"]
            if process is None:
                continue
            try:
                process.wait(timeout=max(0.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                try:
                    process.terminate()
                    process.wait(timeout=0.5)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        self.helpers.clear()
        self.retired.clear()
