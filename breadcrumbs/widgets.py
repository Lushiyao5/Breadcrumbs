from __future__ import annotations

from textual import events
from textual.widgets import Static
from textual.widgets import TextArea
from textual.containers import Vertical
from rich.text import Text


class MiniTrail(Static):
    """A live, nameless view of recorded departures and returns."""

    DEFAULT_CSS = """
    MiniTrail { width: 14; height: 1fr; padding: 0 1; border-left: solid #303a55; }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rows = []
        self.running = False
        self.tracking = False
        self.phase = 0
        self.tooltip = "Recorded focus trail · click or press B for details"

    def on_mount(self):
        self.set_interval(0.4, self._advance_pulse)
        self._draw()

    def set_trace(self, rows, running, tracking):
        self.rows, self.running, self.tracking = rows[-3:], running, tracking
        self._draw()

    def _advance_pulse(self):
        if self.running and self.tracking and self.rows:
            self.phase = (self.phase + 1) % 4
            self._draw()

    def _draw(self):
        from .activity import activity_label
        from .brands import brand_for
        text = Text("TRAIL\n\n", style="dim")
        if not self.rows:
            text.append("│\n○\n\n", style="#78869f")
            text.append("Waiting" if self.tracking else "Not tracking", style="dim")
        else:
            side = False
            for index, row in enumerate(self.rows):
                label = row.get("annotation") or row["classification"]
                branch = label != "planned"
                if branch and not side:
                    text.append("├──╮\n", style="#78869f")
                elif side and not branch:
                    text.append("├──╯\n", style="#70e1c1")
                pulse = index == len(self.rows)-1 and self.running and self.tracking
                node = ("●", "◉", "●", "○")[self.phase] if pulse else "●"
                color = brand_for(row["app"], row["domain"]).color if label not in ("unknown", "away", "excluded") else "#78869f"
                text.append(("│  " if branch else "") + node + "\n", style=color)
                side = branch
            label = self.rows[-1].get("annotation") or self.rows[-1]["classification"]
            text.append("\n" + (activity_label(label) if self.running else "Paused"), style="dim")
        self.update(text)

    def on_click(self):
        self.app.action_branches()


class ReadingCard(Vertical):
    """A short page-turn animation beside stable, readable card text."""

    FRAMES = (
        "  ___ ___\n /   V   \\\n|___/ \\___|",
        "  ___|___\n /   |   \\\n|___/ \\___|",
        "  ___/___\n /  /    \\\n|___/ \\___|",
        "  ___ ___\n /   V   \\\n|___/ \\___|",
    )
    DEFAULT_CSS = """
    ReadingCard { height: auto; }
    #book-icon { height: 3; color: #70e1c1; text-align: center; margin-bottom: 1; }
    #reading-text { height: auto; text-align: center; }
    """

    def compose(self):
        yield Static(self.FRAMES[0], id="book-icon", markup=False)
        yield Static("", id="reading-text", markup=False)

    def on_mount(self) -> None:
        self._frame = len(self.FRAMES)
        self._animated = True
        self._book_icon = self.query_one("#book-icon", Static)
        self.set_interval(0.35, self._turn_page)

    def show_card(self, text: str, animate: bool) -> None:
        self._animated = animate
        self._frame = 0 if animate else len(self.FRAMES)
        self.query_one("#book-icon", Static).update(self.FRAMES[0])
        self.query_one("#reading-text", Static).update(text)

    def _turn_page(self) -> None:
        if self._animated and self.display and self._book_icon.is_mounted and self._frame < len(self.FRAMES):
            self._book_icon.update(self.FRAMES[self._frame])
            self._frame += 1


class CommandBar(Static):
    """A pinned, explicit key guide shared by every screen."""

    DEFAULT_CSS = """
    CommandBar {
        dock: bottom;
        height: auto;
        min-height: 1;
        max-height: 3;
        background: #101522;
        color: #aab4c8;
        text-align: center;
        text-style: bold;
    }
    """


class GoalEditor(TextArea):
    """Scrollable intention editor with lightweight Markdown checklists."""

    DEFAULT_TEXT = "- [ ] "

    def on_focus(self) -> None:
        self.screen.query_one(CommandBar).update(
            "ENTER new task · CTRL+B bullet · F2 check/uncheck · ESC back to timer"
        )

    def on_blur(self) -> None:
        self.screen.query_one(CommandBar).update(
            "SPACE start/pause · B branches · E intentions · H history · C config · CTRL+N new session · ? tour · Q quit"
        )

    def __init__(self, text: str = DEFAULT_TEXT, **kwargs) -> None:
        super().__init__(text, soft_wrap=True, **kwargs)

    def add_bullet(self) -> None:
        row, _ = self.cursor_location
        lines = self.text.split("\n")
        if row < len(lines) and not lines[row].strip():
            self.replace("- [ ] ", (row, 0), (row, len(lines[row])))
        else:
            self.insert("\n- [ ] ")
        self.scroll_cursor_visible()

    def toggle_current(self) -> None:
        row, column = self.cursor_location
        lines = self.text.split("\n")
        if row >= len(lines):
            return
        line = lines[row]
        if line.startswith("- [ ] "):
            replacement = "- [x] " + line[6:]
        elif line.startswith("- [x] ") or line.startswith("- [X] "):
            replacement = "- [ ] " + line[6:]
        else:
            replacement = "- [ ] " + line
        self.replace(replacement, (row, 0), (row, len(line)))
        self.cursor_location = (row, min(len(replacement), column + (0 if line.startswith("- [") else 6)))
        self.scroll_cursor_visible()

    def clear_goals(self) -> None:
        self.load_text(self.DEFAULT_TEXT)
        self.cursor_location = (0, len(self.DEFAULT_TEXT))

    def carry_remaining(self) -> None:
        """Keep unfinished checklist items and free-form notes for the next block."""
        remaining = [line for line in self.text.splitlines()
                     if not line.lstrip().startswith(("- [x]", "- [X]"))]
        self.load_text("\n".join(remaining).strip() or self.DEFAULT_TEXT)

    @property
    def goal_text(self) -> str:
        text = self.text.strip()
        return "" if text in {"- [ ]", "- [x]", "- [X]"} else text

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+b":
            self.add_bullet()
            event.prevent_default()
            event.stop()
            return
        if event.key == "f2":
            self.toggle_current()
            event.prevent_default()
            event.stop()
            return
        if event.key == "enter":
            row, _ = self.cursor_location
            lines = self.text.split("\n")
            if row < len(lines) and lines[row].startswith(("- [ ] ", "- [x] ", "- [X] ")):
                self.insert("\n- [ ] ")
                self.scroll_cursor_visible()
                event.prevent_default()
                event.stop()
                return
        await super()._on_key(event)


class PixelProgress(Static):
    """A crisp, predictable progress meter made from block characters."""

    def __init__(self, *, width: int = 24, **kwargs) -> None:
        super().__init__(**kwargs)
        self.bar_width = width
        self.value = 0.0

    def set_progress(self, value: float) -> None:
        self.value = min(1.0, max(0.0, value))
        filled = round(self.value * self.bar_width)
        bar = "█" * filled + "░" * (self.bar_width - filled)
        self.update(f"{bar}  {self.value:>4.0%}")


class PixelLogo(Static):
    LOGO = """[b]████████╗██╗      ██████╗  ██████╗██╗  ██╗
╚══██╔══╝██║     ██╔═══██╗██╔════╝██║ ██╔╝
   ██║   ██║     ██║   ██║██║     █████╔╝
   ██║   ██║     ██║   ██║██║     ██╔═██╗
   ██║   ███████╗╚██████╔╝╚██████╗██║  ██╗
   ╚═╝   ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝[/b]"""

    def __init__(self, **kwargs) -> None:
        super().__init__(self.LOGO, markup=True, **kwargs)
