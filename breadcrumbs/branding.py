"""The supplied Breadcrumbs bread mark, rendered without image protocols."""
import json
from functools import lru_cache
from importlib.resources import files

from rich.style import Style
from rich.text import Text
from textual.widgets import Static


@lru_cache(maxsize=2)
def logo_text(size: str = 'header') -> Text:
    rows=json.loads((files('breadcrumbs')/'assets/branding/terminal.json').read_text(encoding='utf-8'))[size]
    result=Text(no_wrap=True)
    for y in range(0,len(rows),2):
        if y: result.append('\n')
        for x,top in enumerate(rows[y]):
            bottom=rows[y+1][x] if y+1<len(rows) else None
            if top and bottom: result.append('▀',Style(color=top,bgcolor=bottom))
            elif top: result.append('▀',Style(color=top))
            elif bottom: result.append('▄',Style(color=bottom))
            else: result.append(' ')
    return result


class BreadcrumbsMark(Static):
    DEFAULT_CSS = 'BreadcrumbsMark { width: 12; height: 3; content-align: left middle; }'

    def __init__(self, **kwargs):
        super().__init__(logo_text().copy(), **kwargs)
