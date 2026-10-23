# Terminal pet engine exploration

Tlock currently keeps its sprite and interaction engine native to Textual. This
avoids two terminal renderers competing for keyboard input, mouse tracking, the
alternate screen, and frame timing.

## Projects examined

### Asciimatics

Strong ideas: sprite paths, particle effects, image-to-ASCII conversion,
cross-platform screen handling, and resize-aware scenes.

Integration cost: Asciimatics owns the terminal screen and event loop. Embedding
it in Textual would be fragile; adopting isolated concepts or pre-rendered frame
data is safer than running both renderers.

### PyTermGUI

Strong ideas: expressive terminal markup, a window manager, mouse support, and
SVG/HTML captures.

Integration cost: it is another complete UI framework and is now archived. It
is useful as design reference, not as a new runtime dependency.

### Tuipet and other virtual pets

Strong ideas: half-block Unicode sprites, fixed animation timelines, care-state
machines, and persistent pet state.

Integration cost: game-specific sprite collections may have unclear or
third-party intellectual-property constraints. Tlock should use original,
small, auditable sprites.

## Experiments worth doing

1. Add a native half-block sprite renderer supporting per-cell foreground and
   background colors.
2. Add small completion particles inside the existing mascot widget.
3. Add mouse interactions such as feed, play, and pet without introducing a
   second event loop.
4. Persist happiness and energy locally, but freeze or soften decay while Tlock
   is closed so the companion never punishes absence.
5. Define a documented community pet-pack format containing original frames,
   metadata, attribution, and a declared license.

Any pet-pack loader should validate dimensions and frame counts, reject terminal
control characters, and never execute code from a pack.
