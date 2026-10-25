// Real MV3 extension + real authenticated Python HTTP bridge, isolated browser/profile/database.
const {chromium} = require('../.build-check/node_modules/playwright');
const {spawn} = require('node:child_process');
const {createInterface} = require('node:readline');
const {mkdtempSync} = require('node:fs');
const {resolve, join} = require('node:path');
const assert = require('node:assert/strict');

async function main() {
  const videoDir=process.env.BREADCRUMBS_VIDEO_CAPTURE;
  if(videoDir)require('node:fs').mkdirSync(videoDir,{recursive:true});
  const capture=async(page,name)=>{if(videoDir)await page.locator('main').screenshot({path:join(videoDir,name+'.png')});};
  const pythonPath = process.env.BREADCRUMBS_TEST_PYTHON || resolve(process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
  const python = spawn(pythonPath, ['-X', 'utf8', 'scripts/browser_e2e_host.py'], {stdio: ['pipe','pipe','inherit']});
  const exited = new Promise(resolve=>python.once('exit', resolve));
  const messages = [], waiting = [];
  createInterface({input: python.stdout}).on('line', line => {
    const value = JSON.parse(line);
    if (waiting.length) waiting.shift()(value); else messages.push(value);
  });
  const next = () => messages.length ? Promise.resolve(messages.shift()) : new Promise(resolve => waiting.push(resolve));
  const command = async value => {python.stdin.write(JSON.stringify(value)+'\n'); return next();};
  const credentials = await next(); // stays in memory; never printed
  let context;
  try {
    const extension = resolve('breadcrumbs/assets/browser-extension');
    const profile = mkdtempSync(resolve('.build-check/browser-e2e-'));
    context = await chromium.launchPersistentContext(profile, {
      channel: 'chromium', headless: true, deviceScaleFactor:videoDir?3:1,
      args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`]
    });
    await context.route('https://docs.python.org/**', route => route.fulfill({contentType:'text/html', body:'<title>Python docs fixture</title><h1>Docs</h1>'}));
    await context.route('https://www.youtube.com/**', route => route.fulfill({contentType:'text/html', body:'<title>Video fixture</title><h1>Video</h1>'}));
    let worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
    const extensionId = new URL(worker.url()).host;
    let popup = await context.newPage();
    await popup.goto(`chrome-extension://${extensionId}/popup.html`);
    await popup.locator('#endpoint').fill(credentials.address);
    await popup.locator('#token').fill(credentials.token);
    await popup.locator('#pair').click();
    try {
      await popup.waitForFunction(() => document.querySelector('#status').textContent.includes('Scope picker connected'), null, {timeout:10000});
    } catch (error) {
      const ui = await popup.evaluate(()=>({status:document.querySelector('#status').textContent,error:document.querySelector('#error').textContent}));
      const probe = await worker.evaluate(async ({address,token})=>{
        try {
          const holder = {fetchImpl: fetch};
          const response = await holder.fetchImpl(address+'/v1/status',{headers:{Authorization:'Bearer '+token}});
          return {status:response.status,body:await response.json()};
        }
        catch(error) { return {error:error.message}; }
      },credentials);
      throw new Error('Pairing failed: '+JSON.stringify({ui,probe}));
    }
    console.log('Pairing passed');
    await capture(popup,'extension-paired');
    assert.equal(await popup.locator('#token').inputValue(), '');
    const docs = await context.newPage();
    await docs.goto('https://docs.python.org/3/?fixture=private');
    const sync = () => popup.evaluate(() => chrome.runtime.sendMessage({type:'get-state'}));
    const inspect = () => command({command:'inspect'});
    const until = async (predicate, label='state') => {
      const deadline = Date.now()+10000;
      let last;
      while (Date.now()<deadline) {
        await sync();
        const result = await inspect();
        last = result;
        if (predicate(result)) {console.log('Passed: '+label); return result;}
        await new Promise(resolve => setTimeout(resolve, 150));
      }
      const browser = await worker.evaluate(async()=>({windows:await chrome.windows.getAll(),tabCount:(await chrome.tabs.query({})).length}));
      throw new Error('Browser integration timed out at '+label+': '+JSON.stringify({status:last.status,records:last.records.map(r=>({domain:r.domain,focused:r.focused,tabs:r.tabs.length})),rows:last.rows.map(r=>({app:r.app,domain:r.domain,precision:r.precision})),browser}));
    };
    let result = await until(value => value.tabs.some(tab=>tab.domain==='docs.python.org'), 'tab inventory');
    assert(!JSON.stringify(result).includes('fixture=private'));
    await command({command:'desktop', context:{app:'chrome.exe',title:'Python docs fixture — Google Chrome - Work profile'}});
    await command({command:'policy', active:true, inventory:false});
    await docs.bringToFront();
    result = await until(value => value.rows.some(row=>row.domain==='docs.python.org' && row.classification==='planned'), 'planned docs tab');
    assert.equal(result.scope.domains.length, 0);
    assert.equal(result.scope.pages.length, 1);
    await command({command:'policy', active:true, titles:true});
    await docs.bringToFront();
    result = await until(value => value.rows.at(-1)?.title==='Python docs fixture', 'exact browser tab title is recorded');
    let preview = await sync();
    assert.equal(preview.state.tab_context.title, 'Python docs fixture');
    assert.equal(preview.state.tab_context.domain, 'docs.python.org');
    const video = await context.newPage();
    await video.goto('https://www.youtube.com/watch?v=fixture-one');
    await video.bringToFront();
    await command({command:'desktop', context:{app:'chrome.exe',title:'Video fixture - Google Chrome'}});
    result = await until(value=>value.rows.some(row=>row.domain==='youtube.com' && row.classification==='unclassified'));
    result = await until(value=>value.rows.at(-1)?.title==='Video fixture', 'tab title updates after navigation');
    preview = await sync();
    assert.equal(preview.state.tab_context.title, 'Video fixture');
    const firstKey = result.records.find(record=>record.domain==='youtube.com').page_key;
    await video.goto('https://www.youtube.com/watch?v=fixture-two');
    result = await until(value=>value.records.some(record=>record.domain==='youtube.com' && record.page_key!==firstKey));
    assert(!JSON.stringify(result).includes('fixture-one'));
    assert(!JSON.stringify(result).includes('fixture-two'));
    await docs.bringToFront();
    await command({command:'desktop', context:{app:'chrome.exe',title:'Python docs fixture - Google Chrome'}});
    result = await until(value=>value.rows.at(-1)?.classification==='planned' && value.rows.at(-1)?.domain==='docs.python.org', 'return to exact selected URL');
    await docs.goto('https://docs.python.org/3/?fixture=changed');
    result = await until(value=>value.rows.at(-1)?.domain==='docs.python.org' && value.rows.at(-1)?.classification==='unclassified', 'different query stays out of scope');
    await docs.goto('https://docs.python.org/3/?fixture=private');
    result = await until(value=>value.rows.at(-1)?.domain==='docs.python.org' && value.rows.at(-1)?.classification==='planned', 'exact URL returns to scope again');
    const savedPageKey = result.scope.pages[0].page_key;
    const restarted = await command({command:'restart'});
    assert.equal(restarted.timer_status, 'paused');
    await command({command:'policy', active:true});
    result = await until(value=>value.rows.at(-1)?.domain==='docs.python.org' && value.rows.at(-1)?.classification==='planned', 'selected URL stays in scope after full TUI restart');
    assert.equal(result.scope.pages[0].page_key, savedPageKey);
    assert(result.span_count >= 2);
    // Worker restart ordering is covered in the JS suite. Exercise the user's
    // popup-open path here without restarting the browser's extension target.
    await popup.close();
    popup = await context.newPage();
    await popup.goto(`chrome-extension://${extensionId}/popup.html`);
    await popup.waitForFunction(()=>document.querySelector('#timer-state').textContent==='RUNNING');
    assert.equal(await popup.locator('#timer-name').textContent(), result.status.timer.name);
    console.log('Passed: reopened extension popup immediately detects already-running TUI session');
    // A genuine extension heartbeat must never hide an OS-reported other application.
    await command({command:'desktop', context:{app:'Code.exe',title:'Editor fixture'}});
    result = await until(value=>value.rows.some(row=>row.app==='Code.exe'));
    await command({command:'policy', active:false, inventory:false});
    result = await until(value=>value.records.every(record=>!record.focused && !record.domain));
    const pausedCount = result.rows.length;
    await docs.bringToFront();
    await sync();
    assert.equal((await inspect()).rows.length, pausedCount);
    await command({command:'desktop', context:{app:'Unknown',status:'unknown'}});
    await command({command:'policy', active:true, titles:false});
    result = await until(value=>value.records.some(record=>record.domain==='docs.python.org'));
    assert(result.records.every(record=>record.title===''));
    // Stop and disconnect through real extension messaging/UI, not direct HTTP injection.
    await popup.bringToFront();
    await popup.locator('#stop').click();
    await popup.waitForFunction(()=>document.querySelector('#status').textContent==='Sharing stopped');
    result = await inspect();
    assert(result.records.every(record=>!record.focused));
    await popup.close();
    popup = await context.newPage();
    await popup.goto(`chrome-extension://${extensionId}/popup.html`);
    await popup.waitForFunction(()=>document.querySelector('#timer-state').textContent==='RUNNING');
    await popup.waitForFunction(()=>document.querySelector('#status').textContent==='Sharing stopped');
    console.log('Passed: popup reopen detects active session while sharing stays stopped');
    await popup.waitForFunction(()=>document.querySelector('#timer-primary').textContent==='Pause' && !document.querySelector('#timer-primary').disabled);
    await capture(popup,'extension-running');
    await popup.locator('#timer-primary').click();
    result = await until(value=>value.timer_status==='paused', 'pause timer from extension with sharing stopped');
    await popup.waitForFunction(()=>document.querySelector('#timer-primary').textContent==='Resume' && !document.querySelector('#timer-primary').disabled);
    await capture(popup,'extension-paused');
    await popup.locator('#timer-primary').click();
    result = await until(value=>value.timer_status==='running', 'resume timer from extension');
    await popup.waitForFunction(()=>document.querySelector('#timer-finish').disabled===false);
    await popup.locator('#timer-finish').click();
    await capture(popup,'extension-finish-confirm');
    await popup.locator('#timer-cancel').click();
    assert.equal((await inspect()).timer_status,'running');
    await popup.locator('#timer-finish').click();
    await popup.locator('#timer-confirm').click();
    result = await until(value=>value.recent[0]?.status==='completed' && value.recent[0]?.completion_reason==='early', 'finish timer from extension and save elapsed time');
    assert.equal(result.status.timer.can_control,false);
    await command({command:'dismiss-reflection'});
    await popup.waitForFunction(()=>document.querySelector('#timer-primary').textContent==='Start' && !document.querySelector('#timer-primary').disabled);
    await popup.locator('#timer-primary').click();
    result = await until(value=>value.timer_status==='running' && value.recent[0]?.status==='running', 'start next block from extension');
    assert.equal(result.status.timer.name, 'real-browser-test', 'session name remains stable across remote finish/start');
    await popup.waitForFunction(()=>document.querySelector('#timer-state').textContent==='RUNNING' && document.querySelector('#timer-primary').textContent==='Pause' && !document.querySelector('#timer-primary').disabled);
    await popup.setViewportSize({width:400,height:900});
    await popup.locator('main').screenshot({path:'docs/assets/browser-extension.png'});
    await capture(popup,'extension-next-block');
    await popup.locator('#disconnect').click();
    await popup.waitForFunction(()=>document.querySelector('#status').textContent==='Not paired');
    const storage = await worker.evaluate(()=>chrome.storage.local.get(['token','endpoint','enabled']));
    assert.deepEqual(storage, {});
    console.log('PASS: exact-URL scope selection, deviation/return, full TUI restart/recovery, extension timer start/pause/resume/confirmed finish, browser sharing stop/disconnect, privacy gates.');
    console.log('Desktop deviation was supplied by a fixture; no private desktop/browser profile was inspected.');
  } finally {
    if (context) await context.close();
    await command({command:'close'});
    python.stdin.end();
    assert.equal(await exited, 0, 'Python TUI host must shut down cleanly');
  }
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
