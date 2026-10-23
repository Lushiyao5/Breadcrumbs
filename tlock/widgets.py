from __future__ import annotations

from textual import events
from textual.widgets import Static
from textual.widgets import TextArea


class CommandBar(Static):
    """A pinned, explicit key guide shared by every screen."""

    DEFAULT_CSS = """
    CommandBar {
        dock: bottom;
        height: 1;
        background: #101522;
        color: #aab4c8;
        text-align: center;
        text-style: bold;
    }
    """


class GoalEditor(TextArea):
    """Scrollable intention editor with lightweight Markdown checklists."""

    DEFAULT_TEXT = "- [ ] "

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
