from __future__ import annotations

import random
from itertools import cycle

from textual.widgets import Static

from .timer import TimerStatus


PETS = {
    "mizan": {
        "name": "Mizan",
        "template": "  ╔══════╗ {prop}\n  ║ {eyes}  ║\n  ║  {mouth}   ║\n  ╚═╤══╤═╝\n    {feet}",
    },
    "byte": {
        "name": "Byte",
        "template": "  ▲   ▲   {prop}\n ╭───────╮\n │ {eyes}  │\n │   {mouth}   │\n ╰─{feet}─╯",
    },
    "nova": {
        "name": "Nova",
        "template": "   ▄████▄  {prop}\n  █ {eyes} █\n  █  {mouth}  █\n  ▀█▄█▄█▀\n   {feet}",
    },
    "sprig": {
        "name": "Sprig",
        "template": "    ♣     {prop}\n  ▄████▄\n █ {eyes} █\n █  {mouth}  █\n  ▀{feet}▀",
    },
}

MOODS = {
    "ready": (("◉ ◉", "‿", "", "▀  ▀"), ("— —", "‿", "", " ▀▀ ")),
    "focus": (("• •", "▬", "▐▐", "▄  ▄"), ("• •", "▬", "▐▐", " ▄▄ ")),
    "break": (("^ ^", "‿", "♫", "▀▄ ▄▀"), ("^ ^", "‿", "♪", " ▀▄▀ ")),
    "paused": (("– –", "·", "Ⅱ", "▀  ▀"),),
    "done": (("★ ★", "‿", "★", "▄  ▄"), ("★ ★", "‿", "✦", " ▄▄ ")),
    "pet": (("^ ^", "‿", "♥", "▀  ▀"), ("^ ^", "‿", "♡", " ▀▀ ")),
}


class PixelMascot(Static):
    def __init__(self, pet_key: str = "mizan", **kwargs) -> None:
        super().__init__(**kwargs)
        self.pet_key = pet_key if pet_key in PETS else "mizan"
        self.mood = "ready"
        self._frames = cycle(self._frames_for(self.mood))
        self._pet_ticks = 0

    @property
    def pet_name(self) -> str:
        return str(PETS[self.pet_key]["name"])

    def _frames_for(self, mood: str) -> tuple[str, ...]:
        template = str(PETS[self.pet_key]["template"])
        return tuple(
            template.format(eyes=eyes, mouth=mouth, prop=prop, feet=feet)
            for eyes, mouth, prop, feet in MOODS[mood]
        )

    def _reset_frames(self, *, update: bool = False) -> None:
        self._frames = cycle(self._frames_for(self.mood))
        if update:
            self.update(next(self._frames))

    def on_mount(self) -> None:
        self._reset_frames(update=True)
        self.set_interval(0.42, self.animate)

    def set_state(self, status: TimerStatus, is_break: bool) -> None:
        mood = "break" if is_break and status is TimerStatus.RUNNING else status.value
        mood = {"running": "focus", "finished": "done"}.get(mood, mood)
        if mood != self.mood:
            self.mood = mood
            self._reset_frames()

    def spawn(self) -> tuple[str, str]:
        choices = [key for key in PETS if key != self.pet_key]
        self.pet_key = random.choice(choices)
        self._pet_ticks = 0
        self._reset_frames(update=True)
        return self.pet_key, self.pet_name

    def pet(self) -> None:
        self._pet_ticks = 5
        self._frames = cycle(self._frames_for("pet"))
        self.update(next(self._frames))

    def animate(self) -> None:
        if self._pet_ticks:
            self._pet_ticks -= 1
            if not self._pet_ticks:
                self._reset_frames()
        self.update(next(self._frames))
