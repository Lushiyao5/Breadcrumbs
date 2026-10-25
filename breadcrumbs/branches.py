"""Separate focus trail and scope screens; the timer layout stays compact."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Select, SelectionList, Static, Switch
from textual.widgets.option_list import Option

from .activity import activity_label, app_key, clean, domain_name
from .brands import activity_brand, brand_for, render_logo
from .config import Settings
from .widgets import CommandBar


def duration(seconds: float) -> str:
    minutes, seconds = divmod(max(0, int(seconds)), 60)
    return f"{minutes:02d}:{seconds:02d}"


def scope_summary(scope: dict | None) -> str:
    if not scope:
        return "No saved scope. Choose Scope / source to set your working context."
    parts = [clean(app) for app in scope.get("apps", [])]
    if scope.get("pages"):
        parts.append(f"{len(scope['pages'])} selected browser pages")
    if scope.get("domains"):
        parts.append(f"{len(scope['domains'])} domains")
    parts.extend(brand_for(agent.get("kind", "")).label for agent in scope.get("agents", []))
    return "Scope: " + (" · ".join(parts) if parts else "no targets selected · choose Scope / source")


def trail_prompts(rows: list[dict]) -> list[Text]:
    prompts = []
    on_branch = False
    for row in rows:
        label = row.get("annotation") or row["classification"]
        if label in ("break", "block"):
            text = Text("○   ", style="#78b8ff" if label == "break" else "#78869f")
            text.append(datetime.fromtimestamp(row["started_at"]).strftime("%H:%M:%S") + "  ", style="dim")
            text.append(row["app"] + f"  {duration(row['ended_at'] - row['started_at'])}  [{activity_label(label)}]")
            prompts.append(text)
            on_branch = False
            continue
        branch = label != "planned"
        color = {"planned": "#70e1c1", "supporting": "#78b8ff", "unclassified": "#ffd166"}.get(label, "#78869f")
        brand = activity_brand(row)
        text = Text()
        if branch and not on_branch:
            text.append("│╲\n", style=color)
        elif on_branch and not branch:
            text.append("│╱  Back in scope\n", style="#70e1c1")
        text.append("│ ● " if branch else "●   ", style=brand.color)
        timestamp = datetime.fromtimestamp(row["started_at"]).strftime("%H:%M:%S")
        text.append(f"{timestamp}  ", style="dim")
        name = brand.label if brand.key != "generic" else clean(row["app"])
        text.append(name, style=brand.color)
        from .terminal import terminal_hint
        if terminal_hint(row["app"], row["title"]):
            text.append(" (title hint)", style="dim")
        detail = row["domain"] or row["title"]
        if detail:
            text.append(" · " + clean(detail, 65), style=brand.color)
        text.append(f"  {duration(row['ended_at'] - row['started_at'])}  [{activity_label(label)}]", style=color)
        prompts.append(text)
        on_branch = branch
    return prompts


class StartSessionScreen(ModalScreen[str | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]
    CSS = """
    StartSessionScreen { align: center middle; background: #090b12e8; }
    #start-card { width: 64; height: auto; padding: 1 2; background: #151927; border: round #70e1c1; }
    #start-card Button { width: 100%; margin-top: 1; }
    #start-card Static { height: auto; }
    """

    def __init__(self, name: str, has_scope: bool):
        super().__init__()
        self.session_name, self.has_scope = name, has_scope

    def compose(self) -> ComposeResult:
        with Vertical(id="start-card"):
            yield Static("Start your focus block", classes="modal-title")
            yield Static(self.session_name, markup=False)
            yield Static("Choose where you intend to work. Activity is captured only while this focus block runs.")
            yield Button("Choose scope and start", id="start-scope", variant="success")
            if self.has_scope:
                yield Button("Use previous scope", id="start-previous")
            yield Button("Continue without tracking", id="start-untracked")
            yield Button("Cancel", id="start-cancel")
        yield CommandBar("TAB choose · ENTER select · ESC cancel")

    def action_cancel(self):
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        event.stop()
        self.dismiss({"start-scope": "scope", "start-previous": "previous",
                      "start-untracked": "untracked"}.get(event.button.id))


class PairBrowserScreen(ModalScreen[None]):
    BINDINGS = [("escape", "close", "Close")]
    CSS = """
    PairBrowserScreen { align: center middle; background: #090b12e8; }
    #pair-card { width: 90%; max-width: 96; height: auto; padding: 1 2;
        background: #151927; border: round #70e1c1; }
    #pair-card Static { height: auto; margin: 1 0; }
    #pair-card Button { width: 100%; }
    """

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def compose(self):
        from importlib.resources import files
        with Vertical(id="pair-card"):
            yield Static("Connect your browser", classes="modal-title")
            yield Static("1. Open chrome://extensions (or edge://extensions), enable Developer mode.\n"
                         "2. Load unpacked → choose this folder:")
            yield Input(str(files("breadcrumbs") / "assets" / "browser-extension"), id="extension-path")
            yield Static("3. Open the Breadcrumbs extension. Paste the address and pairing token, then Pair / Start.\n"
                         "Keep this token on your own computer. Select text and copy with Ctrl+C.")
            yield Input(self.bridge.address, id="bridge-address")
            yield Input(self.bridge.token, id="bridge-token", password=True)
            yield Button("Show / hide token", id="pair-reveal")
            yield Button("Back to scope", id="pair-close", variant="success")
        yield CommandBar("TAB move · CTRL+C copy selected text · ESC back")

    def action_close(self):
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        event.stop()
        if event.button.id == "pair-reveal":
            widget = self.query_one("#bridge-token", Input)
            widget.password = not widget.password
        else:
            self.action_close()


class ScopeScreen(ModalScreen[Settings | None]):
    BINDINGS = [("escape", "cancel", "Cancel"), ("ctrl+s", "save", "Save")]
    CSS = """
    ScopeScreen { align: center middle; background: #090b12e8; }
    #scope-card { width: 90%; max-width: 90; height: 90%; padding: 1 2;
        background: #151927; border: round #70e1c1; }
    #scope-card Label { height: auto; margin-top: 1; }
    #scope-card Select, #scope-card Input { height: 3; }
    #scope-connection { height: 3; }
    #scope-apps { height: 9; }
    #scope-help { height: auto; color: #aab4c8; margin-bottom: 1; }
    #scope-error { height: auto; color: #ff6b6b; }
    #scope-actions { grid-size: 2; grid-gutter: 1; height: 3; margin-top: 1; }
    """

    def __init__(self, settings: Settings, candidates: list[str], agents=None, bridge=None, starting=False):
        super().__init__()
        self.settings = settings
        self.candidates = candidates
        self.agents = agents or []
        self.bridge = bridge
        self.starting = starting
        self.pages = {page["page_key"]: page for page in settings.activity_pages}
        self._page_signature = None

    def compose(self) -> ComposeResult:
        chosen = {app_key(value) for value in self.settings.activity_apps}
        apps = sorted({app_key(value) for value in self.candidates} | chosen)
        with VerticalScroll(id="scope-card"):
            yield Static("Focus ambit · choose your working context", classes="modal-title")
            yield Static(
                "Choose apps, terminal agents, domains or individual browser pages.\n"
                "Breadcrumbs captures foreground context during running focus/custom blocks.\n"
                "Browser detail uses the bundled extension; no ActivityWatch installation.",
                id="scope-help",
            )
            yield Label("Activity source")
            yield Select(
                (("Off", "off"), ("Breadcrumbs · apps + paired browser", "integrated")),
                value="off" if self.settings.activity_source == "off" else "integrated",
                allow_blank=False, id="scope-source",
            )
            yield Label("Planned apps · available windows / suggested apps · Space selects")
            yield SelectionList(*[(app, app, app in chosen) for app in apps], id="scope-apps")
            yield Label("Running terminal agents · selecting adds a temporary title marker")
            if not self.agents:
                yield Static("No live CLI candidates found. Open Claude Code/Codex, then reopen scope.", markup=False)
            selected_agents = {agent["id"] for agent in self.settings.activity_agents}
            available_agents = {agent["id"]: agent for agent in self.settings.activity_agents + self.agents}
            yield SelectionList(*[(agent["label"], key, key in selected_agents)
                                  for key, agent in available_agents.items()], id="scope-agents")
            yield Static("", id="scope-agent-status", markup=False)
            yield Label("Browser pages · connect the extension in Config → Browser connection")
            yield Button("Refresh open tabs", id="scope-refresh")
            yield Static("Waiting for paired browser…", id="scope-browser-status", markup=False)
            yield SelectionList(*[(page.get("title") or page["domain"], key, True)
                                  for key, page in self.pages.items()], id="scope-pages")
            yield Label("Additional app names (comma separated)")
            yield Input(placeholder="code, WindowsTerminal, firefox", id="scope-extra-apps")
            yield Label("Planned domains (comma separated; narrows browser matches)")
            yield Input(", ".join(self.settings.activity_domains), placeholder="docs.python.org, github.com", id="scope-domains")
            yield Label("Show and store window/tab titles")
            yield Switch(self.settings.activity_titles, id="scope-titles")
            yield Static(
                "Page identity is a URL hash; raw URLs never leave the extension. Titles may\n"
                "contain document names. Private browser tabs are excluded by the extension.\n"
                "App-only capture cannot reliably recognize private windows. Unsupported\n"
                "terminal panes remain host-level context; running is not the same as active.",
                id="scope-help-note", markup=False,
            )
            yield Label("", id="scope-error")
            with Grid(id="scope-actions"):
                yield Button("Save and start" if self.starting else "Save scope", id="save-scope", variant="success")
                yield Button("Cancel", id="cancel-scope")
            if self.starting:
                yield Button("Start without tracking", id="scope-untracked")
        yield CommandBar("SPACE toggle app · TAB move · CTRL+S save · ESC cancel")

    def action_cancel(self):
        self.dismiss(None)

    def on_mount(self):
        agents = self.query_one("#scope-agents", SelectionList)
        agents.styles.height = 5
        agents.display = bool(self.agents or self.settings.activity_agents)
        self.query_one("#scope-pages", SelectionList).styles.height = 7
        self.set_interval(0.5, self.refresh_pages)
        self.refresh_pages()

    def refresh_pages(self):
        if not self.bridge:
            self.query_one("#scope-browser-status", Static).update("Bridge unavailable. App scope still works.")
            return
        agent_ids = {agent.get("id") for agent in self.settings.activity_agents}
        self.query_one("#scope-agent-status", Static).update(self.bridge.state.agent_problem(agent_ids))
        tabs = self.bridge.state.browser_tabs()
        signature = repr(tabs)
        if signature == self._page_signature:
            return
        self._page_signature = signature
        widget = self.query_one("#scope-pages", SelectionList)
        chosen = set(widget.selected)
        for tab in tabs:
            key = tab["page_key"]
            if key:
                self.pages[key] = {field: tab[field] for field in ("page_key", "domain", "title")}
        widget.clear_options()
        live_keys = {tab["page_key"] for tab in tabs}
        widget.add_options([(f"{page.get('title') or page['domain']} · {page['domain']}" +
                             (" (saved URL; not open)" if tabs and key in chosen and key not in live_keys else ""), key, key in chosen)
                            for key, page in self.pages.items()])
        self.query_one("#scope-browser-status", Static).update(
            f"{len(tabs)} available tabs · select a page or use a domain below" if tabs else
            "No tabs yet. Pair the extension; reports may take up to 30 seconds."
        )

    def action_save(self):
        try:
            raw = self.query_one("#scope-domains", Input).value.split(",")
            domains = [domain_name(value.strip()) for value in raw if value.strip()]
            if any(not domain or " " in domain for domain in domains):
                raise ValueError("Use domain names such as docs.python.org.")
            apps = self.query_one("#scope-apps", SelectionList).selected
            extras = self.query_one("#scope-extra-apps", Input).value.split(",")
            apps = sorted(set(apps) | {app_key(app.strip()) for app in extras if app.strip()})
            available_agents = {agent["id"]: agent for agent in self.settings.activity_agents + self.agents}
            self.dismiss(replace(
                self.settings, activity_source=str(self.query_one("#scope-source", Select).value),
                activity_apps=apps, activity_domains=domains,
                activity_titles=self.query_one("#scope-titles", Switch).value,
                activity_pages=[self.pages[key] for key in self.query_one("#scope-pages", SelectionList).selected],
                activity_agents=[available_agents[key] for key in self.query_one("#scope-agents", SelectionList).selected],
            ))
        except ValueError as error:
            self.query_one("#scope-error", Label).update(str(error))

    def on_button_pressed(self, event: Button.Pressed):
        event.stop()
        if event.button.id == "save-scope":
            self.action_save()
        elif event.button.id == "cancel-scope":
            self.action_cancel()
        elif event.button.id == "scope-untracked":
            self.dismiss(replace(self.settings, activity_source="off"))
        elif event.button.id == "scope-refresh":
            self._page_signature = None
            self.refresh_pages()


def visit_details(database, row):
    from .terminal import terminal_hint
    from .brands import activity_brand
    brand = activity_brand(row)
    label = row.get("annotation") or row["classification"]
    start = datetime.fromtimestamp(row["started_at"]).strftime("%Y-%m-%d %H:%M:%S")
    end = datetime.fromtimestamp(row["ended_at"]).strftime("%H:%M:%S")
    text = "\n".join(value for value in (brand.label, row["domain"], row["title"]) if value) + "\n\n"
    text += f"{activity_label(label)} · {duration(row['ended_at'] - row['started_at'])}\n{start} → {end}\n"
    capture = {"window": "App window", "tab": "Browser tab", "browser-focus": "Browser focus",
               "terminal-marker": "Verified terminal agent", "block": "Timer"}.get(row["precision"], "Activity")
    text += f"Captured: {capture}\n\n"
    if row.get("notice") and row["notice"] not in ("Desktop window", "Bundled browser bridge",
            "Verified process + active terminal title marker"):
        text += row["notice"] + "\n\n"
    hint = terminal_hint(row["app"], row["title"])
    if hint:
        text += f"Terminal host: {row['app']}\nProgram hint: {brand.label} (window title; not process verified)\n\n"
    elif row["precision"] == "terminal-marker":
        text += "Agent verified by live process and foreground terminal marker.\n\n"
    scope = database.span_scope(row["span_id"])
    if row["precision"] == "window":
        from .activity import is_browser
        from .terminal import is_terminal
        if is_browser(row["app"]) and (scope.get("pages") or scope.get("domains")):
            text += "Only the browser window was captured. Its selected page could not be verified.\n\n"
        elif is_terminal(row["app"]) and scope.get("agents"):
            text += "Only the terminal host was captured. The selected agent was not verified.\n\n"
    if label in ("break", "block"):
        text += "Timer span · no app/browser capture during breaks.\n\n" if label == "break" else "Timer span · no activity observations recorded.\n\n"
    else:
        text += "A in scope\nS supporting detour\nV deviation\n\n"
    return brand, text.rstrip()


class ActivityDetailScreen(ModalScreen[None]):
    BINDINGS = [("escape", "close", "Back"), ("a", "label('planned')", "In scope"),
                ("s", "label('supporting')", "Supporting"), ("v", "label('unclassified')", "Deviation")]
    CSS = """
    ActivityDetailScreen { align: center middle; background: #090b12e8; }
    #visit-card { width: 90%; max-width: 86; height: 90%; padding: 1 2;
        background: #151927; border: round #70e1c1; }
    #visit-scroll { height: 1fr; }
    #visit-logo { height: 8; margin-bottom: 1; }
    #visit-info { height: auto; }
    #visit-close { width: 100%; margin-top: 1; }
    """

    def __init__(self, database, row):
        super().__init__()
        self.database, self.row = database, dict(row)

    def compose(self):
        with Vertical(id="visit-card"):
            yield Static("Activity details", classes="modal-title")
            with VerticalScroll(id="visit-scroll"):
                yield Static("", id="visit-logo")
                yield Static("", id="visit-info", markup=False)
            yield Button("Back to branches", id="visit-close")
        yield CommandBar("A in scope · S supporting · V deviation · scroll details · ESC back")

    def on_mount(self):
        self._refresh()

    def _refresh(self):
        brand, text = visit_details(self.database, self.row)
        self.query_one("#visit-logo", Static).update(render_logo(brand))
        self.query_one("#visit-info", Static).update(text)

    def action_label(self, label):
        if self.row["classification"] in ("unknown", "away", "excluded", "break", "block"):
            self.notify("This observation keeps its recorded label.")
            return
        self.database.annotate_activity(self.row["id"], label)
        self.row["annotation"] = label
        self._refresh()

    def action_close(self):
        self.dismiss(None)

    def on_button_pressed(self, event):
        event.stop()
        self.action_close()


class TrailOptionList(OptionList):
    """Follow the newest visit after wrapped rows change the virtual height."""

    def watch_virtual_size(self):
        if self.is_mounted:
            self.call_after_refresh(self._follow_latest_layout)

    def _follow_latest_layout(self):
        if self.option_count and self.highlighted == self.option_count - 1:
            self.scroll_end(animate=False, immediate=True)


class BranchesScreen(ModalScreen[None]):
    BINDINGS = [
        ("escape", "back", "Back"), ("b", "close", "Close"),
        ("s", "supporting", "Supporting"), ("a", "planned", "In scope"),
        ("v", "deviation", "Deviation"), ("u", "deviation", "Deviation"),
        ("end", "latest", "Latest activity"),
    ]
    CSS = """
    BranchesScreen { align: center middle; background: #090b12e8; }
    #branches-card { width: 94%; max-width: 132; height: 84%; max-height: 38; padding: 1 2;
        background: #131827; border: round #70e1c1; }
    #branches-heading { height: 1; text-style: bold; color: #70e1c1; }
    #branch-session { height: 3; }
    #branches-note { height: auto; max-height: 2; color: #aab4c8; margin-bottom: 1; }
    #branches-body { height: 1fr; }
    #trail { width: 1fr; height: 1fr; border: none; background: #0d111d; }
    #trail > .option-list--option-highlighted { background: #20384a; color: #edf2f7; }
    #branch-detail { width: 40; padding: 0 1; overflow-y: auto; border-left: solid #303a55; }
    #branch-detail-heading { height: auto; color: #70e1c1; margin-bottom: 1; }
    #branch-logo { height: 8; margin-bottom: 1; }
    #branch-info { height: auto; }
    #branch-actions { height: 3; grid-size: 3; grid-gutter: 1; margin-top: 1; }
    #branch-actions Button { min-width: 8; }
    BranchesScreen.narrow #branch-detail { width: 30; }
    BranchesScreen.short #branches-card { height: 90%; padding: 0 1; }
    BranchesScreen.short #branches-note { display: none; }
    BranchesScreen.short #branch-detail-heading { height: 1; margin-bottom: 0; }
    BranchesScreen.short #branch-actions { margin-top: 0; }
    BranchesScreen.short #branch-logo { height: 1; margin-bottom: 0; }
    """

    def __init__(self, database, session_id: int | None = None):
        super().__init__()
        self.database = database
        self.session_id = database.session_identity(session_id)[0] if session_id else None
        self._rows = []
        self._signature = None
        self._session_rows = database.named_sessions()
        if self.session_id and self.session_id not in {row["id"] for row in self._session_rows}:
            row = database.connection.execute("SELECT * FROM sessions WHERE id = ?", (self.session_id,)).fetchone()
            if row is not None:
                self._session_rows.insert(0, dict(row))

    def compose(self) -> ComposeResult:
        choices = [(row["name"] or f"Block {row['id']}", str(row["id"])) for row in self._session_rows]
        value = str(self.session_id) if self.session_id in {r["id"] for r in self._session_rows} else (choices[0][1] if choices else Select.BLANK)
        with Vertical(id="branches-card"):
            yield Static("Focus branches", id="branches-heading")
            yield Select(choices, value=value, allow_blank=True, prompt="Choose a focus block", id="branch-session")
            yield Static("", id="branches-note", markup=False)
            with Horizontal(id="branches-body"):
                yield TrailOptionList(id="trail")
                with VerticalScroll(id="branch-detail"):
                    yield Static("Activity details", id="branch-detail-heading", markup=False)
                    yield Static("", id="branch-logo")
                    yield Static("Select a visit to inspect its context.", id="branch-info", markup=False)
            with Grid(id="branch-actions"):
                yield Button("Latest", id="branch-latest")
                yield Button("Scope / source", id="branch-scope")
                yield Button("Close", id="branch-close")
        yield CommandBar("↑↓/click activity · Details follow selection · END latest · A/S/V label · ESC close")

    def on_mount(self):
        self.set_class(self.size.width < 100, "narrow")
        self.set_class(self.size.height < 32, "short")
        selected = self.query_one("#branch-session", Select).value
        self.session_id = int(selected) if selected is not Select.BLANK else None
        self._refresh_trail(initial=True)
        self.call_after_refresh(self._refresh_trail)
        self.set_interval(1.0, self._refresh_trail)
        self.query_one("#trail", OptionList).focus()

    def on_resize(self):
        self.set_class(self.size.width < 100, "narrow")
        self.set_class(self.size.height < 32, "short")
        self.call_after_refresh(self._detail)
        self.call_after_refresh(self._keep_selection_visible)

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "branch-session":
            if event.value != event.select.value:
                return  # Ignore an older queued selection after the current value changed.
            chosen = int(event.value) if event.value is not Select.BLANK else None
            if chosen != self.session_id:
                self.session_id = chosen
                self._signature = None
                self.query_one("#trail", OptionList).clear_options()
                self._refresh_trail()

    def _refresh_trail(self, initial: bool = False):
        if (not initial and not self.is_mounted) or not len(self.query("#trail")):
            return
        previous_rows = self._rows
        self._rows = self.database.session_trail(self.session_id) if self.session_id else []
        signature = repr(self._rows)
        self.query_one("#branches-heading", Static).update("Focus branches · recorded context")
        self.query_one("#branches-note", Static).update(
            scope_summary(self.database.load_scope(self._rows[-1]["session_id"] if self._rows else self.session_id) if self.session_id else None) + "\n" +
            ("In scope = main lane · Deviation = outside scope · Unknown = context not verified."
             if self._rows else "No visits recorded yet. Choose a scope and run a focus block.")
        )
        if signature != self._signature:
            options = self.query_one("#trail", OptionList)
            old = options.highlighted
            was_last = old is None or old == options.option_count - 1
            prompts = trail_prompts(self._rows)
            old_ids = [str(row["id"]) for row in previous_rows]
            ids = [str(row["id"]) for row in self._rows]
            if options.option_count != len(old_ids) or ids[:len(old_ids)] != old_ids:
                options.clear_options()
                options.add_options([Option(prompt, id=str(row["id"])) for row, prompt in zip(self._rows, prompts)])
            else:
                old_prompts = trail_prompts(previous_rows)
                for index, prompt in enumerate(prompts[:len(old_ids)]):
                    if prompt != old_prompts[index]:
                        options.replace_option_prompt_at_index(index, prompt)
                options.add_options([Option(prompt, id=str(row["id"]))
                    for row, prompt in zip(self._rows[len(old_ids):], prompts[len(old_ids):])])
            if self._rows:
                options.highlighted = len(self._rows) - 1 if was_last else min(old, len(self._rows) - 1)
                if was_last:
                    self.call_after_refresh(self._scroll_latest)
            self._signature = signature
        self._detail()

    def _detail(self):
        options = self.query_one("#trail", OptionList)
        if options.highlighted is None or options.highlighted >= len(self._rows):
            self.query_one("#branch-logo", Static).update("")
            self.query_one("#branch-info", Static).update("Select a visit to inspect its context.")
            return
        row = self._rows[options.highlighted]
        brand, text = visit_details(self.database, row)
        self.query_one("#branch-logo", Static).update(render_logo(brand, compact=self.has_class("short")))
        self.query_one("#branch-info", Static).update(text)

    def _scroll_latest(self):
        options = self.query_one("#trail", OptionList)
        if options.highlighted == options.option_count - 1:
            options.scroll_end(animate=False, immediate=True)

    def _keep_selection_visible(self):
        options = self.query_one("#trail", OptionList)
        if options.highlighted == options.option_count - 1:
            self._scroll_latest()
        else:
            options.scroll_to_highlight()

    def action_latest(self):
        options = self.query_one("#trail", OptionList)
        if options.option_count:
            options.highlighted = options.option_count - 1
            self.call_after_refresh(self._scroll_latest)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        event.stop()
        row = next((row for row in self._rows if str(row["id"]) == event.option.id), None)
        if row is not None:
            self._detail()
            self.call_after_refresh(self._keep_selection_visible)

    def action_back(self):
        self.action_close()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted):
        self._detail()

    def _label(self, label: str):
        options = self.query_one("#trail", OptionList)
        if options.highlighted is None or not self._rows:
            return
        row = self._rows[options.highlighted]
        if row["classification"] in ("away", "unknown", "excluded", "break", "block"):
            self.notify("Idle, unknown, and excluded intervals retain their observation labels.")
            return
        self.database.annotate_activity(row["id"], label)
        self._signature = None
        self._refresh_trail()

    def action_supporting(self): self._label("supporting")
    def action_planned(self): self._label("planned")
    def action_unclassified(self): self._label("unclassified")
    def action_deviation(self): self._label("unclassified")
    def action_close(self): self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        event.stop()
        if event.button.id == "branch-close":
            self.action_close()
        elif event.button.id == "branch-scope":
            self.app.action_scope()
        elif event.button.id == "branch-latest":
            self.action_latest()
