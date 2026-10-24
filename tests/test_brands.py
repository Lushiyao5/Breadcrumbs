import hashlib
import json
from importlib.resources import files

import pytest
from rich.cells import cell_len
from rich.text import Text

from breadcrumbs.brands import BRANDS, brand_for, render_logo


@pytest.mark.parametrize(
    ("app", "key"),
    [
        ("Code.exe", "vscode"),
        (r"C:\Program Files\Microsoft VS Code\Code.exe", "vscode"),
        ("/usr/share/code/code", "vscode"),
        ("code-insiders", "vscode"),
        ("chrome.exe", "chrome"),
        ("google-chrome.desktop", "chrome"),
        ("Firefox.exe", "firefox"),
        ("Spotify.exe", "spotify"),
        ("WindowsTerminal.exe", "terminal"),
        ("pwsh.exe", "terminal"),
        ("gnome-terminal-server", "terminal"),
        ("claude", "claude"),
        ("claude-code", "claude_code"),
        ("codex.exe", "codex"),
        ("OpenAI", "openai"),
        ("GitHubDesktop.exe", "github"),
    ],
)
def test_explicit_process_aliases(app, key):
    assert brand_for(app).key == key


@pytest.mark.parametrize(
    ("domain", "key"),
    [
        ("https://www.youtube.com/watch?v=example", "youtube"),
        ("music.youtube.com", "youtube"),
        ("youtu.be", "youtube"),
        ("open.spotify.com", "spotify"),
        ("WWW.CLAUDE.AI:443", "claude"),
        ("code.claude.com", "claude_code"),
        ("chatgpt.com", "chatgpt"),
        ("platform.openai.com", "openai"),
        ("github.com", "github"),
        ("code.visualstudio.com", "vscode"),
    ],
)
def test_browser_domain_takes_priority(domain, key):
    assert brand_for("chrome.exe", domain).key == key


def test_titles_and_lookalike_domains_do_not_guess_identity():
    assert brand_for("Building a Codex integration - Terminal").key == "generic"
    assert brand_for("mycode.exe").key == "generic"
    assert brand_for("youtube.com").key == "generic"
    assert brand_for("chrome.exe", "youtube.com.evil.example").key == "chrome"
    assert brand_for("chrome.exe", "notyoutube.com").key == "chrome"
    assert brand_for("").label == "Application"
    assert "\n" not in brand_for("unknown\napp").label


def test_source_masks_are_bundled_and_match_source_vectors():
    root = files("breadcrumbs").joinpath("assets", "brands")
    masks = json.loads(root.joinpath("masks.json").read_text(encoding="utf-8"))
    for asset in {brand.asset for brand in BRANDS.values()}:
        source = root.joinpath(f"{asset}.svg").read_text(encoding="utf-8").replace("\r\n", "\n")
        assert hashlib.sha256(source.encode()).hexdigest() == masks[asset]["source_sha256"]
        for size in (4, 16):
            rows = masks[asset][str(size)]
            assert len(rows) == size
            assert any(int(row, 16) for row in rows)
            assert all(0 <= int(row, 16) < 2 ** size for row in rows)


def test_every_brand_renders_without_an_icon_font_or_image_dependency():
    for brand in BRANDS.values():
        logo = render_logo(brand)
        assert isinstance(logo, Text)
        assert len(logo.plain.splitlines()) == 8
        assert all(cell_len(line) == 16 for line in logo.plain.splitlines())
        compact = render_logo(brand, compact=True)
        assert "\n" not in compact.plain
        assert cell_len(compact.plain) == 2
        assert compact.spans
    assert render_logo("codex").plain == render_logo(BRANDS["openai"]).plain
    assert "not a Codex-specific" in BRANDS["codex"].mark_name


def test_apps_have_distinct_stable_colors_including_terminal_hosts():
    apps = ["Code.exe", "chrome.exe", "Spotify.exe", "claude-code", "claude", "codex",
            "chatgpt", "openai", "github", "WindowsTerminal.exe", "pwsh.exe", "notepad.exe", "explorer.exe"]
    colors = [brand_for(app).color for app in apps]
    assert len(set(colors)) == len(apps)
    assert brand_for("C:/Windows/notepad.exe").color == brand_for("NOTEPAD.exe").color
    assert brand_for("codex").color == brand_for("codex").color
    assert brand_for("chrome.exe", "youtube.com").color != brand_for("chrome.exe").color
