from __future__ import annotations

import platform
import threading
import time


MELODIES = {
    "arcade": ((523, 90), (659, 90), (784, 90), (1047, 260)),
    "victory": ((659, 110), (784, 110), (988, 160), (784, 80), (988, 300)),
    "gentle": ((523, 160), (659, 180), (784, 320)),
}


def play_completion(enabled: bool = True, theme: str = "arcade") -> None:
    if not enabled:
        return
    threading.Thread(target=_play, args=(theme,), daemon=True).start()


def _play(theme: str = "arcade") -> None:
    if platform.system() == "Windows":
        try:
            import winsound

            for frequency, duration in MELODIES.get(theme, MELODIES["arcade"]):
                winsound.Beep(frequency, duration)
                time.sleep(0.025)
            return
        except (ImportError, RuntimeError):
            pass
    print("\a\a", end="", flush=True)
