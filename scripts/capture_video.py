"""Real pilot-driven TUI frames for a continuous, privacy-safe tutorial."""
import asyncio
import json
import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from textual.widgets import Input, OptionList
from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.activity import Context
from breadcrumbs.widgets import GoalEditor
from breadcrumbs.branches import BranchesScreen

OUT = Path(__file__).resolve().parents[1] / 'videos' / 'recording'

async def main():
    OUT.mkdir(exist_ok=True)
    frames=[]; cues=[]
    previous=os.environ.get('BREADCRUMBS_HOME')
    old_color=os.environ.pop('NO_COLOR',None)
    try:
        with TemporaryDirectory(prefix='breadcrumbs-video-') as home:
            os.environ['BREADCRUMBS_HOME']=home
            app=BreadcrumbsApp(session_name='fix-the-login-flow')
            app.settings.sound_enabled=False
            app.settings.reading_mode='quotes'
            app.settings.book_animation=False
            app.settings.browser_bridge_port=0
            async with app.run_test(size=(120,38)) as pilot:
                async def snap(at,label):
                    await pilot.pause(.02)
                    name=f'frame-{len(frames):03d}'
                    (OUT/(name+'.svg')).write_text(app.export_screenshot(title='Breadcrumbs'),encoding='utf-8')
                    frames.append(dict(at=at,file=name+'.png',label=label))
                async def click(at,selector):
                    widget=app.screen.query_one(selector)
                    r=widget.region
                    cues.append(dict(at=at,x=(r.x+r.width/2)/120,y=(r.y+r.height/2)/38,click=True))
                    await pilot.click(selector)
                    await snap(at,selector)
                await snap(10,'home')
                await pilot.press('e')
                await pilot.press('end')
                await snap(13,'intentions')
                text='Fix the login redirect'
                for i,char in enumerate(text):
                    await pilot.press('space' if char==' ' else char)
                    await snap(14+i*.09,'typing')
                await pilot.press('ctrl+b')
                await snap(17,'add checklist')
                for i,char in enumerate('Add a regression test'):
                    await pilot.press('space' if char==' ' else char)
                    await snap(18+i*.09,'typing')
                await pilot.press('escape')
                await snap(22,'ready')
                await click(25,'#start')
                await click(29,'#start-untracked')
                # Keep recording deterministic while displaying a real running block.
                app._activity_next_poll=float('inf')
                await snap(32,'focus running')
                await click(36,'#start')
                await click(39,'#start')
                await snap(42,'resumed')
                # Real stored observations from an isolated documentation fixture.
                sid=app.active_session_id
                start=time.time()-300
                app.database.close_spans(sid, time.time())
                span=app.database.open_span(sid,start)
                app._span_id=span
                visits=[('Code.exe','Fix the login redirect','','planned'),
                        ('chrome.exe','Python docs','docs.python.org','planned'),
                        ('chrome.exe','A useful tutorial','youtube.com','supporting'),
                        ('Spotify.exe','Choose a playlist','','unclassified'),
                        ('Code.exe','Back to the login fix','','planned')]
                for i,(name,title,domain,label) in enumerate(visits):
                    row=app.database.record_activity(sid,span,Context(name,title,domain,source='fixture'),label,start+i*45)
                    app.database.connection.execute('UPDATE activity_intervals SET ended_at=? WHERE id=?',(start+(i+1)*45,row))
                app.action_branches()
                await pilot.pause(.05)
                app.screen.query_one('#trail',OptionList).highlighted=4
                await snap(45,'branches latest')
                trail=app.screen.query_one('#trail',OptionList)
                for at,index in [(49,1),(52,2),(55,3),(58,4)]:
                    trail.highlighted=index
                    await snap(at,'sidebar follows selection')
                    r=trail.region
                    cues.append(dict(at=at,x=(r.x+20)/120,y=(r.y+index+1)/38,click=False))
                await pilot.press('escape')
                await snap(62,'back home')
                await click(65,'#settings')
                await snap(69,'config')
                await pilot.press('escape')
                app.action_browser_connection()
                await snap(73,'browser connection')
                await pilot.press('escape')
                await snap(80,'return to work')
                app.action_toggle()
                await snap(83,'paused end')
        (OUT/'timeline.json').write_text(json.dumps(dict(frames=frames,cues=cues,duration=88),indent=2),encoding='utf-8')
        print(f'Captured {len(frames)} real app states')
    finally:
        if previous is None: os.environ.pop('BREADCRUMBS_HOME',None)
        else: os.environ['BREADCRUMBS_HOME']=previous
        if old_color is not None: os.environ['NO_COLOR']=old_color

if __name__=='__main__': asyncio.run(main())
