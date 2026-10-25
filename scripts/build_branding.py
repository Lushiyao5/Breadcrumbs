"""Translate the supplied logo's bread mark into terminal-native colour cells.

The original PNG is preserved. Runtime needs only the generated JSON and Rich.
"""
import json
from pathlib import Path
from PIL import Image

root=Path(__file__).resolve().parents[1]
source=Image.open(root/'breadcrumbs/assets/branding/logo.png').convert('RGB')
# Bounds of the bread-and-trail symbol in the supplied 1254px square artwork.
mark=source.crop((302,278,944,808))
sizes={}
for name,width,height in [('header',10,6),('welcome',24,20)]:
    pixels=mark.resize((width,height),Image.Resampling.NEAREST)
    rows=[]
    for y in range(height):
        row=[]
        for x in range(width):
            r,g,b=pixels.getpixel((x,y))
            palette=[(15,36,54),(255,174,13),(255,245,222)]
            colour=min(palette,key=lambda c:sum((a-b)**2 for a,b in zip(c,(r,g,b))))
            row.append(None if min(r,g,b)>235 else '#%02x%02x%02x'%colour)
        rows.append(row)
    sizes[name]=rows
(root/'breadcrumbs/assets/branding/terminal.json').write_text(json.dumps(sizes,separators=(',',':')),encoding='utf-8')
print('Built terminal logo data from the original artwork')
