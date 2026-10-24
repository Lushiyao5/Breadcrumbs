"""Offline reading cards. Quotes are original Breadcrumbs reminders."""

import random

from .verses import VERSES

QUOTES = (
    "You do not need to finish everything. Give this next step your attention.",
    "A small, honest effort still moves the work forward.",
    "Start where you are. One useful action is enough to begin.",
    "Rest is part of the work. Return with a little more room to think.",
    "A difficult block does not decide the rest of your day.",
    "Choose a task small enough to start, then let yourself begin.",
    "You can revise the plan without giving up on the intention.",
    "Progress can be quiet. Keep a record of what you did.",
    "Your attention deserves a clear task and a kind pace.",
    "There is time to begin again. Take the next available step.",
    "Do what is possible now. Leave room to learn as you go.",
    "One completed step is more useful than a perfect imaginary plan.",
)


def next_card(mode: str, previous: int | None = None) -> tuple[int, str]:
    count = len(VERSES) if mode == "quran" else len(QUOTES)
    index = random.choice([i for i in range(count) if i != previous])
    if mode == "quran":
        verse = VERSES[index]
        label = " · excerpt" if verse.excerpt else ""
        return index, f"{verse.arabic}\n\n{verse.translation}\n\n{verse.reference}{label} · English meaning"
    return index, f"{QUOTES[index]}\n\nBreadcrumbs · original reminder"
