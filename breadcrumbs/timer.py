from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class TimerKind(StrEnum):
    FOCUS = "focus"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"
    CUSTOM = "custom"


class TimerStatus(StrEnum):
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"


@dataclass(slots=True)
class TimerEngine:
    duration_seconds: int
    kind: TimerKind = TimerKind.FOCUS
    status: TimerStatus = TimerStatus.READY
    remaining_seconds: float = 0
    _deadline: float | None = None

    def __post_init__(self) -> None:
        if self.duration_seconds <= 0:
            raise ValueError("Timer duration must be positive")
        self.remaining_seconds = float(self.duration_seconds)

    def configure(self, seconds: int, kind: TimerKind) -> None:
        if seconds <= 0:
            raise ValueError("Timer duration must be positive")
        self.duration_seconds = seconds
        self.kind = kind
        self.status = TimerStatus.READY
        self.remaining_seconds = float(seconds)
        self._deadline = None

    def start(self, now: float | None = None) -> None:
        if self.status in (TimerStatus.READY, TimerStatus.PAUSED):
            current = time.monotonic() if now is None else now
            self._deadline = current + self.remaining_seconds
            self.status = TimerStatus.RUNNING

    def pause(self, now: float | None = None) -> None:
        if self.status is TimerStatus.RUNNING:
            self.tick(now)
            if self.status is not TimerStatus.FINISHED:
                self.status = TimerStatus.PAUSED
                self._deadline = None

    def reset(self) -> None:
        self.remaining_seconds = float(self.duration_seconds)
        self.status = TimerStatus.READY
        self._deadline = None

    def tick(self, now: float | None = None) -> bool:
        if self.status is not TimerStatus.RUNNING or self._deadline is None:
            return False
        current = time.monotonic() if now is None else now
        self.remaining_seconds = max(0.0, self._deadline - current)
        if self.remaining_seconds <= 0:
            self.status = TimerStatus.FINISHED
            self._deadline = None
            return True
        return False

    @property
    def elapsed_seconds(self) -> int:
        return max(0, self.duration_seconds - int(self.remaining_seconds + 0.999))

    @property
    def progress(self) -> float:
        return min(1.0, max(0.0, 1 - self.remaining_seconds / self.duration_seconds))

    @property
    def display(self) -> str:
        rounded = max(0, int(self.remaining_seconds + 0.999))
        hours, remainder = divmod(rounded, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
