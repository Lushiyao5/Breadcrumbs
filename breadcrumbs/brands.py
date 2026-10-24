"""Recognize explicit app/domain identities and render real source logo shapes.

No icon font, image protocol, raster library, or network access is required.
The 16x16 masks are generated from the licensed SVGs in assets/brands.
See docs/BRANDS.md for attribution and the compact rendering limitation.
"""

from __future__ import annotations

import json
import colorsys
import hashlib
import re
from dataclasses import dataclass, replace
from functools import lru_cache
from importlib.resources import files
from urllib.parse import urlsplit

from rich.text import Text


@dataclass(frozen=True, slots=True)
class Brand:
    key: str
    label: str
    color: str
    asset: str
    mark_name: str

    @property
    def name(self) -> str:
        """Readable label; retained as an alias for callers using name."""
        return self.label


BRANDS = {
    "youtube": Brand("youtube", "YouTube", "#FF0033", "youtube", "YouTube play-button mark"),
    "spotify": Brand("spotify", "Spotify", "#1ED760", "spotify", "Spotify mark"),
    "chrome": Brand("chrome", "Chrome", "#4285F4", "googlechrome", "Google Chrome mark"),
    "firefox": Brand("firefox", "Firefox", "#FF7139", "firefoxbrowser", "Firefox Browser mark"),
    "vscode": Brand("vscode", "Visual Studio Code", "#23A8F2", "vscode", "Microsoft Codicons VS Code mark"),
    "claude": Brand("claude", "Claude", "#D97757", "claude", "Claude asterisk"),
    "claude_code": Brand("claude_code", "Claude Code", "#FFB86C", "claude", "Claude asterisk (shared brand mark)"),
    "openai": Brand("openai", "OpenAI", "#70E1C1", "openai", "OpenAI company mark"),
    "codex": Brand("codex", "Codex", "#C4A7FF", "openai", "OpenAI company mark; not a Codex-specific logo"),
    "chatgpt": Brand("chatgpt", "ChatGPT", "#9ACD66", "openai", "OpenAI company mark"),
    "github": Brand("github", "GitHub", "#F0F6FC", "github", "GitHub Octocat mark"),
    "terminal": Brand("terminal", "Terminal", "#AAB4C8", "terminal", "Generic Microsoft Codicons terminal indicator"),
    "generic": Brand("generic", "Application", "#AAB4C8", "window", "Generic Microsoft Codicons window indicator"),
}

_APP_ALIASES = {
    "youtube": "youtube",
    "spotify": "spotify",
    "chrome": "chrome",
    "google chrome": "chrome",
    "googlechrome": "chrome",
    "google-chrome": "chrome",
    "google-chrome-stable": "chrome",
    "com.google.chrome": "chrome",
    "firefox": "firefox",
    "firefox-esr": "firefox",
    "firefox browser": "firefox",
    "org.mozilla.firefox": "firefox",
    "code": "vscode",
    "code-insiders": "vscode",
    "code - insiders": "vscode",
    "visual studio code": "vscode",
    "visualstudiocode": "vscode",
    "com.visualstudio.code": "vscode",
    "claude": "claude",
    "claude-code": "claude_code",
    "claude code": "claude_code",
    "codex": "codex",
    "openai": "openai",
    "chatgpt": "chatgpt",
    "github": "github",
    "githubdesktop": "github",
    "github desktop": "github",
    "windowsterminal": "terminal",
    "windowsterminalpreview": "terminal",
    "windows terminal": "terminal",
    "terminal": "terminal",
    "gnome-terminal": "terminal",
    "gnome-terminal-server": "terminal",
    "org.gnome.terminal": "terminal",
    "konsole": "terminal",
    "alacritty": "terminal",
    "wezterm": "terminal",
    "wezterm-gui": "terminal",
    "kitty": "terminal",
    "xterm": "terminal",
    "powershell": "terminal",
    "pwsh": "terminal",
    "cmd": "terminal",
    "bash": "terminal",
    "zsh": "terminal",
    "fish": "terminal",
}

# Only the explicit domain argument is inspected as a URL. A window title or
# executable name containing a service name is never treated as a domain.
_DOMAINS = (
    ("youtube.com", "youtube"), ("youtu.be", "youtube"),
    ("spotify.com", "spotify"),
    ("claude.ai", "claude"), ("code.claude.com", "claude_code"),
    ("chatgpt.com", "chatgpt"), ("openai.com", "openai"),
    ("github.com", "github"),
    ("code.visualstudio.com", "vscode"),
)


def _hostname(domain: str) -> str:
    if not domain:
        return ""
    try:
        parsed = urlsplit(domain if "://" in domain else "//" + domain)
        return (parsed.hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def brand_for(app: str, domain: str = "") -> Brand:
    """Resolve a browser domain first, otherwise an exact process/app alias.

    App may be an executable path, executable basename, or known display name.
    Unknown apps get a neutral window indicator and retain their readable name.
    This function identifies a brand; it does not classify a focus branch.
    """
    hostname = _hostname((domain or "").strip())
    for known, key in _DOMAINS:
        if hostname == known or hostname.endswith("." + known):
            return BRANDS[key]
    basename = re.split(r"[/\\]", app.strip())[-1]
    normalized = re.sub(r"\.(exe|app|bin|desktop)$", "", basename, flags=re.IGNORECASE).lower()
    key = _APP_ALIASES.get(normalized)
    if key:
        if key == "terminal":
            return replace(BRANDS[key], color=_app_color(normalized))
        return BRANDS[key]
    # Sanitize display-only control characters, without trying to parse titles.
    label = "".join(c for c in basename if c.isprintable()).strip()[:80]
    return Brand("generic", label or "Application", _app_color(normalized), "window", BRANDS["generic"].mark_name)


def _app_color(identity: str) -> str:
    """Stable, bright colors across launches, independent of Python's hash seed."""
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    hue = int.from_bytes(digest[:4], "big") / 2**32
    saturation = 0.45 + digest[4] / 255 * 0.2
    rgb = colorsys.hsv_to_rgb(hue, saturation, 0.95)
    return "#" + "".join(f"{round(channel * 255):02X}" for channel in rgb)


@lru_cache(maxsize=1)
def _masks() -> dict:
    resource = files("breadcrumbs").joinpath("assets", "brands", "masks.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def render_logo(brand: Brand | str, *, compact: bool = False) -> Text:
    """Render a source-derived logo as Rich Text.

    Default: 16 columns x 8 rows, using foreground half-block cells.
    Compact: 2 columns x 1 row, using a 4x4 braille thumbnail. Such a tiny mark
    is inherently lossy; display brand.label beside it for identification.
    Strings may be BRANDS keys or process/app names.
    """
    if isinstance(brand, str):
        brand = BRANDS.get(brand) or brand_for(brand)
    size = 4 if compact else 16
    rows = [int(row, 16) for row in _masks()[brand.asset][str(size)]]
    result = Text(no_wrap=True, overflow="crop")

    def pixel(x: int, y: int) -> bool:
        return bool(rows[y] & (1 << (size - x - 1)))

    if compact:
        dots = ((0, 0, 0), (0, 1, 1), (0, 2, 2), (1, 0, 3),
                (1, 1, 4), (1, 2, 5), (0, 3, 6), (1, 3, 7))
        for x in (0, 2):
            value = sum(1 << bit for dx, y, bit in dots if pixel(x + dx, y))
            result.append(chr(0x2800 + value) if value else " ", style=brand.color)
        return result
    for y in range(0, size, 2):
        if y:
            result.append("\n")
        for x in range(size):
            upper, lower = pixel(x, y), pixel(x, y + 1)
            character = "█" if upper and lower else "▀" if upper else "▄" if lower else " "
            result.append(character, style=brand.color if upper or lower else None)
    return result
