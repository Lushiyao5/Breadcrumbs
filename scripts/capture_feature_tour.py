"""Capture every public feature from the real app using isolated demo data."""
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from textual.widgets import Input, OptionList, Select, SelectionList, Switch, TextArea
from textual.containers import VerticalScroll
from breadcrumbs.app import BreadcrumbsApp
from breadcrumbs.activity import Context
from breadcrumbs.branches import ScopeScreen, BranchesScreen
from breadcrumbs.widgets import GoalEditor
from breadcrumbs.timer import TimerKind, TimerStatus

OUT=Path(__file__).resolve().parents[1]/'videos/feature-recording'

async def main():
    OUT.mkdir(exist_ok=True)
    old=os.environ.get('BREADCRUMBS_HOME'); colour=os.environ.pop('NO_COLOR',None)
    manifest={};cli={}
    try:
        with TemporaryDirectory(prefix='breadcrumbs-complete-guide-') as home:
            os.environ['BREADCRUMBS_HOME']=home
            app=BreadcrumbsApp(session_name='ship-the-login-fix',show_onboarding=True)
            app.settings.sound_enabled=False;app.settings.browser_bridge_port=0
            app.settings.book_animation=False;app.settings.reading_mode='quotes'
            app._activity_next_poll=float('inf')
            async with app.run_test(size=(120,38)) as pilot:
                async def snap(name):
                    await pilot.pause(.05)
                    svg=app.export_screenshot(title='Breadcrumbs')
                    svg=re.sub(r'@font-face\s*\{[^}]*\}', '',svg)
                    svg=svg.replace('Fira Code','Consolas')
                    svg='\n'.join(line.rstrip() for line in svg.splitlines())+'\n'
                    (OUT/f'{name}.svg').write_text(svg,encoding='utf-8')
                    manifest[name]=dict(file=f'{name}.svg',width=1482,height=977.2)
                await snap('tour')
                await pilot.press('right');await snap('tour-next')
                await pilot.press('escape');await snap('home')
                await pilot.press('e','end')
                for i,ch in enumerate('Fix the login redirect'):
                    await pilot.press('space' if ch==' ' else ch)
                    if i%3==0:await snap(f'type-{i:02d}')
                await snap('intention')
                await pilot.press('ctrl+b')
                for ch in 'Add a regression test':await pilot.press('space' if ch==' ' else ch)
                await snap('checklist')
                await pilot.press('f2');await snap('checked')
                await pilot.press('escape','p');await snap('presets')
                await pilot.click('#preset-50');await snap('extended')
                await pilot.click('#custom-minutes')
                await pilot.press('7');await pilot.click('#custom');await snap('custom')
                await pilot.press('1');await snap('focus-preset')
                await pilot.click('#start');await snap('start-choices')
                await pilot.press('escape')
                fixture=replace(app.settings,activity_source='integrated',activity_apps=['code'],activity_domains=['docs.python.org'],activity_titles=True,
                    activity_pages=[{'domain':'docs.python.org','title':'Python documentation','page_key':'fixture-docs-hash'}],
                    activity_agents=[{'id':'fixture-codex','kind':'codex','label':'Codex Â· example terminal','pid':0}])
                app.push_screen(ScopeScreen(fixture,['code','chrome','windowsterminal'],agents=fixture.activity_agents))
                await snap('scope-apps')
                app.screen.query_one('#scope-agents').scroll_visible(animate=False)
                await snap('scope-agents')
                app.screen.query_one('#scope-pages').scroll_visible(animate=False)
                await snap('scope-pages')
                app.screen.query_one('#scope-domains').scroll_visible(animate=False)
                await snap('scope-domains')
                await pilot.press('escape')
                await pilot.click('#start');await pilot.click('#start-untracked')
                await snap('running')
                await pilot.click('#start');await snap('paused')
                await pilot.click('#start');await snap('resumed')
                sid=app.active_session_id;start=time.time()-360
                app.database.close_spans(sid,time.time());span=app.database.open_span(sid,start);app._span_id=span
                app.database.save_scope(sid,{'apps':['code'],'domains':['docs.python.org']})
                visits=[('Code.exe','Fix the login redirect','','planned'),('chrome.exe','Python documentation','docs.python.org','planned'),
                    ('chrome.exe','A useful walkthrough','youtube.com','supporting'),('Spotify.exe','Pick a playlist','','unclassified'),
                    ('Code.exe','Back to the login fix','','planned'),('WindowsTerminal.exe','Codex review','','planned')]
                for i,(name,title,domain,label) in enumerate(visits):
                    row=app.database.record_activity(sid,span,Context(name,title,domain,source='fixture'),label,start+i*45)
                    app.database.connection.execute('UPDATE activity_intervals SET ended_at=? WHERE id=?',(start+(i+1)*45,row))
                app.action_branches();await pilot.pause(.05)
                trail=app.screen.query_one('#trail',OptionList)
                trail.highlighted=0;await snap('branches')
                for idx,name in [(1,'branch-docs'),(2,'branch-supporting'),(3,'branch-deviation'),(4,'branch-return'),(5,'branch-terminal')]:
                    trail.highlighted=idx;await snap(name)
                trail.highlighted=3;await pilot.press('s');await snap('branch-annotated')
                await pilot.press('end');await snap('branch-latest')
                await pilot.press('escape')
                # Actual early finish decision and reflection workflow.
                app.action_finish();await snap('finish-decision')
                await pilot.click('#finish-early');await snap('reflection')
                app.screen.query_one('#actual-work',TextArea).load_text('Fixed the redirect and added a regression test. Docs helped; the playlist was a detour.')
                app.screen.query_one('#rating',Input).value='4';await snap('reflection-written')
                await pilot.press('ctrl+s');await snap('after-reflection')
                await pilot.press('h');await snap('history');await pilot.press('escape')
                await pilot.press('2');await snap('short-break-ready')
                await pilot.click('#start');await snap('short-break-running')
                app.timer.status=TimerStatus.FINISHED;app._complete_timer();await pilot.pause(.05)
                app.action_branches();await pilot.pause(.05);await pilot.press('end');await snap('break-in-trail');await pilot.press('escape')
                await pilot.press('3');await snap('long-break')
                await pilot.press('1')
                app.action_settings();await pilot.pause(.08);await snap('settings-top')
                app.screen.query_one('#ui-theme',Select).value='gameboy'
                app.screen.query_one('#pet-enabled',Switch).value=True
                await pilot.press('ctrl+s');await snap('gameboy')
                await pilot.press('m');await snap('pet');await pilot.press('n');await snap('new-pet')
                app.action_settings();await pilot.pause(.08);app.screen.query_one('#ui-theme',Select).value='sunset'
                await pilot.press('ctrl+s');await snap('sunset')
                app.action_settings();await pilot.pause(.08);app.screen.query_one('#ui-theme',Select).value='midnight'
                app.screen.query_one('#sound-theme').scroll_visible(animate=False);await snap('sound-settings')
                app.screen.query_one('#sound-theme',Select).value='gentle';await snap('sound-pack')
                app.screen.query_one('#reading-mode').scroll_visible(animate=False);await snap('reading-settings')
                app.screen.query_one('#reading-mode',Select).value='quran'
                app.screen.query_one('#reading-scope',Select).value='breaks'
                app.screen.query_one('#reading-minutes',Input).value='2'
                app.screen.query_one('#book-animation',Switch).value=True
                app.screen.query_one('#auto-focus').scroll_visible(animate=False);await snap('automation-settings')
                await pilot.press('ctrl+s');await snap('midnight-companion')
                app.settings.reading_mode='quotes';app.settings.reading_scope='all';app._reading_due=0
                app._reading_mode='quotes';app._tick();app._refresh_view();await pilot.pause(.2)
                app.screen.query_one('#verse').scroll_visible(animate=False)
                await snap('reading-card')
                app.action_browser_connection();await snap('browser-pairing');await pilot.press('escape')
                # Save a real recoverable block. No user data or live context.
                app._tracking_settings=replace(app.settings,activity_source='off')
                app._begin_block();app.timer.pause();app._checkpoint();await snap('checkpoint')
                app.action_tour();await snap('tour-replay');await pilot.press('escape')
            for key,args in [('sessions',['sessions']),('export',['export','--output',str(Path(home)/'sessions.json')]),
                             ('activity-export',['export','--activity','--output',str(Path(home)/'activity.json')])]:
                result=subprocess.run([sys.executable,'-m','breadcrumbs',*args],capture_output=True,text=True,encoding='utf-8')
                cli[key]=dict(command='breadcrumbs '+' '.join(args).replace(home,'<local-folder>'),output=result.stdout.replace(home,'<local-folder>'),returncode=result.returncode)
            recovered=BreadcrumbsApp()
            recovered.settings.browser_bridge_port=0
            async with recovered.run_test(size=(120,38)) as pilot:
                app=recovered
                await snap('recovery')
                await pilot.click('#recover');await snap('recovered-paused')
                await pilot.press('ctrl+n');await snap('new-session-decision')
                await pilot.click('#end-session');await snap('explicit-new-session')
            (OUT/'cli.json').write_text(json.dumps(cli,indent=2),encoding='utf-8')
            (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
            print(f'Captured {len(manifest)} real feature states and {len(cli)} actual CLI operations')
    finally:
        if old is None:os.environ.pop('BREADCRUMBS_HOME',None)
        else:os.environ['BREADCRUMBS_HOME']=old
        if colour is not None:os.environ['NO_COLOR']=colour

if __name__=='__main__':asyncio.run(main())
