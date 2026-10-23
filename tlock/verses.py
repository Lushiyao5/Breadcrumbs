from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Verse:
    arabic: str
    translation: str
    reference: str


VERSES = (
    Verse(
        "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا",
        "Indeed, with hardship comes ease.",
        "Ash-Sharh 94:5",
    ),
    Verse(
        "وَقُل رَّبِّ زِدْنِي عِلْمًا",
        "And say: My Lord, increase me in knowledge.",
        "Taha 20:114",
    ),
    Verse(
        "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا",
        "Allah does not burden a soul beyond what it can bear.",
        "Al-Baqarah 2:286",
    ),
    Verse(
        "إِنَّ اللَّهَ مَعَ الصَّابِرِينَ",
        "Indeed, Allah is with the patient.",
        "Al-Baqarah 2:153",
    ),
    Verse(
        "فَاذْكُرُونِي أَذْكُرْكُمْ",
        "Remember Me; I will remember you.",
        "Al-Baqarah 2:152",
    ),
    Verse(
        "وَمَن يَتَوَكَّلْ عَلَى اللَّهِ فَهُوَ حَسْبُهُ",
        "Whoever puts their trust in Allah, He is sufficient for them.",
        "At-Talaq 65:3",
    ),
)


def random_verse(previous: Verse | None = None) -> Verse:
    choices = [verse for verse in VERSES if verse != previous] or list(VERSES)
    return random.choice(choices)
