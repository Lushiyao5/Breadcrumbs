"""Small local word library for readable, unique session names."""

import re
import secrets

ADJECTIVES = (
    "amber", "brave", "bright", "calm", "cozy", "curious", "dancing", "gentle",
    "golden", "happy", "hopeful", "little", "lucky", "mellow", "merry", "misty",
    "nimble", "patient", "quiet", "sleepy", "steady", "sunny", "tiny", "velvet",
)
NOUNS = (
    "badger", "bamboo", "cedar", "cloud", "comet", "fern", "finch", "fox",
    "garden", "heron", "jasmine", "lantern", "maple", "meadow", "moon", "otter",
    "panda", "pebble", "puffin", "robin", "sparrow", "sprout", "star", "willow",
)


def generate_name() -> str:
    return f"{secrets.choice(ADJECTIVES)}-{secrets.choice(NOUNS)}-{secrets.token_hex(2)}"


def normalize_name(value: str) -> str:
    name = re.sub(r"[\s_]+", "-", value.strip().lower())
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,58}[a-z0-9]|[a-z0-9]", name):
        raise ValueError("Use 1–60 letters, numbers, or hyphens; start and end with a letter or number.")
    return name
