# App and service marks

The focus context UI uses real vector silhouettes converted into terminal
pixels. It does not require a Nerd Font, an image-capable terminal, a network
request, or an image library at runtime.

The original SVGs and their licenses are bundled in
`breadcrumbs/assets/brands/`. Runtime rendering reads precomputed masks from
`masks.json`; Rich supplies the colored text.

## Sources

| Display identity | Artwork |
| --- | --- |
| YouTube | Simple Icons `youtube.svg`, version 13.0.0 |
| Spotify | Simple Icons `spotify.svg`, version 13.0.0 |
| Chrome | Simple Icons `googlechrome.svg`, version 13.0.0 |
| Firefox | Simple Icons `firefoxbrowser.svg`, version 13.0.0 |
| Claude / Claude Code | Simple Icons `claude.svg`, commit `30053a0f492fd192740ad001031b3091be060986` |
| OpenAI / Codex / ChatGPT | Simple Icons `openai.svg`, version 13.0.0 |
| GitHub | Simple Icons `github.svg`, version 13.0.0 |
| Visual Studio Code | Microsoft Codicons `src/icons/vscode.svg`, commit `5a6ad49557af022f97987cb3cfc3412b5d03f554` |
| Terminal / unknown application | Microsoft Codicons `terminal.svg` / `window.svg`, same commit |

[Simple Icons 13.0.0](https://github.com/simple-icons/simple-icons/tree/13.0.0)
uses [CC0 1.0](https://github.com/simple-icons/simple-icons/blob/13.0.0/LICENSE.md).
The newer Claude vector uses the same
[Simple Icons license](https://github.com/simple-icons/simple-icons/blob/30053a0f492fd192740ad001031b3091be060986/LICENSE.md).
[Microsoft Codicons](https://github.com/microsoft/vscode-codicons/tree/5a6ad49557af022f97987cb3cfc3412b5d03f554)
artwork is licensed under
[CC BY 4.0](https://github.com/microsoft/vscode-codicons/blob/5a6ad49557af022f97987cb3cfc3412b5d03f554/LICENSE).
Microsoft and the Codicons contributors are credited in the bundled
`NOTICE.md`, which also records the resizing and color adaptation.

These are monochrome source marks in a display accent color, not full-color
product icons. They identify the represented application; they are not part of
our own logo. Trademarks belong to their respective owners. In particular, the
OpenAI company mark beside Codex is not a claim that it is a dedicated Codex
logo. Terminal and unknown-app indicators are generic.

## API

```python
from breadcrumbs.brands import brand_for, render_logo

brand = brand_for("chrome.exe", "https://www.youtube.com/watch?v=example")
# brand.label == "YouTube"
# brand.color is a Rich-compatible color; brand.mark_name records the artwork.
detail_widget.update(render_logo(brand))
```

`brand_for(app, domain="")` checks the explicit domain first, then exact app
aliases and executable basenames. It does not inspect a window title to guess
a URL, infer what a user is doing inside a terminal, or classify an activity
as productive. A title containing "Codex" is not enough to identify the Codex
process. Claude's desktop and CLI process names may be indistinguishable;
`claude` uses the broad Claude label, while `claude-code` identifies Claude Code.

Default rendering is 16 terminal columns by eight rows using upper/lower block
cells. `render_logo(brand, compact=True)` is a two-column, one-row braille
thumbnail derived from a 4x4 mask. Detail is lost at that size: a status bar
must include the readable brand label, rather than relying on the tiny mark.
Both use ordinary Unicode characters; the terminal still needs a font capable
of displaying block and braille characters.

## Regenerating masks

The runtime has no Node dependency. Maintainers can use `@resvg/resvg-js`
during development to rasterize the checked-in SVGs:

```powershell
node breadcrumbs/assets/brands/rasterize.cjs ./.build-check/node_modules/@resvg/resvg-js
```

The script prints replacement JSON; update `masks.json` from that output.
It records normalized source hashes and generates both supported sizes.
The 16x16 alpha masks use a threshold of 96/255; the very small 4x4 thumbnails
use 24/255 to preserve thin features.
