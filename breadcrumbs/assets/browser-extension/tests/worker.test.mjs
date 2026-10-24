import assert from "node:assert/strict";
import test from "node:test";
import {webcrypto} from "node:crypto";
import {BrowserBridge} from "../background.mjs";
import {describeTab, digest, formatRemaining, normalizeEndpoint, normalizeTimer, timerPrimaryAction} from "../core.mjs";

if (!globalThis.crypto) globalThis.crypto = webcrypto;

const TOKEN = "test-local-token-123456789";
const ENDPOINT = "http://127.0.0.1:43127";

test("reported tab preview follows navigation and immediately honors title consent", async () => {
  const tabs = [tab()];
  const f = fixture({status: {active: true, include_titles: true}, tabs});
  await f.bridge.sync();
  assert.equal((await f.bridge.state()).tab_context.title, "A helpful tutorial");
  tabs[0] = tab({title: "Python docs", url: "https://docs.python.org/3/"});
  await f.bridge.sync();
  let context = (await f.bridge.state()).tab_context;
  assert.equal(context.title, "Python docs");
  assert.equal(context.domain, "docs.python.org");
  f.remoteStatus.include_titles = false;
  await f.bridge.refreshStatus();
  context = (await f.bridge.state()).tab_context;
  assert.equal(context.title, "");
  assert.equal(context.title_shared, false);
  await f.bridge.setEnabled(false);
  assert.equal((await f.bridge.state()).tab_context, null);
});

test("private/internal tabs and stale status never leave a previous tab preview", async () => {
  const tabs = [tab()];
  const f = fixture({status: {active: true, include_titles: true}, tabs});
  await f.bridge.sync();
  tabs[0] = tab({incognito: true});
  await f.bridge.sync();
  assert.equal((await f.bridge.state()).tab_context, null);
  tabs[0] = tab({url: "chrome://settings"});
  await f.bridge.sync();
  assert.equal((await f.bridge.state()).tab_context, null);
  tabs[0] = tab();
  await f.bridge.sync();
  f.bridge.lastStatusAt = performance.now() - 16000;
  assert.equal((await f.bridge.state()).tab_context, null);
});

test("native worker fetch retains its required global receiver", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async function () {
    assert.equal(this, globalThis);
    return {ok: true, json: async () => ({pairing: true, active: false, inventory_requested: false})};
  };
  try {
    const {api} = fixture();
    const bridge = new BrowserBridge(api);
    assert.equal((await bridge.status({endpoint: ENDPOINT, token: TOKEN})).pairing, true);
  } finally {
    globalThis.fetch = original;
  }
});
const tab = (changes = {}) => ({
  id: 7, windowId: 3, title: "A helpful tutorial",
  url: "https://www.youtube.com/watch?v=video-one&secret=local-only#chapter",
  incognito: false, ...changes
});
const event = () => {
  const listeners = [];
  return {addListener: (listener) => listeners.push(listener), fire: (...args) => listeners.forEach((listener) => listener(...args))};
};
function storageArea(data = {}) {
  return {
    data,
    async get(keys) { return Object.fromEntries(keys.filter((key) => key in data).map((key) => [key, data[key]])); },
    async set(values) { Object.assign(data, values); },
    async remove(keys) { keys.forEach((key) => delete data[key]); }
  };
}
function fixture({paired = true, status = {}, tabs = [tab()], window = {}, local = null, session = null} = {}) {
  const requests = [];
  const reads = {tabs: 0, windows: 0};
  const api = {
    storage: {
      local: storageArea(local || (paired ? {endpoint: ENDPOINT, token: TOKEN, enabled: true} : {})),
      session: storageArea(session || {})
    },
    tabs: {
      onActivated: event(), onUpdated: event(), onRemoved: event(),
      async query(query) { reads.tabs += 1; return query.active ? tabs.filter((item) => item.windowId === query.windowId).slice(0, 1) : tabs; }
    },
    windows: {
      WINDOW_ID_NONE: -1, onFocusChanged: event(),
      async getLastFocused() { reads.windows += 1; return {id: 3, focused: true, incognito: false, type: "normal", ...window}; }
    },
    alarms: {
      onAlarm: event(), created: [], cleared: [],
      async create(name, options) { this.created.push([name, options]); },
      async clear(name) { this.cleared.push(name); }
    },
    runtime: {onMessage: event(), onStartup: event(), onInstalled: event()}
  };
  const remoteStatus = {pairing: true, active: false, inventory_requested: false, include_titles: false, ...status};
  const fetchImpl = async (url, options) => {
    requests.push({url, ...options, payload: options.body ? JSON.parse(options.body) : null});
    return {ok: true, status: url.endsWith("/v1/control") ? 202 : 200, async json() { return {...remoteStatus}; }};
  };
  const bridge = new BrowserBridge(api, fetchImpl);
  const posts = () => requests.filter((request) => request.payload);
  return {api, bridge, requests, reads, posts, remoteStatus};
}

test("connection endpoint stays on the exact HTTP loopback origin", () => {
  assert.equal(normalizeEndpoint(ENDPOINT + "/"), ENDPOINT);
  for (const endpoint of [
    "https://127.0.0.1:1234", "http://localhost:1234", "http://127.0.0.1.evil.test:1234",
    "http://127.0.0.1:1234/path", "http://user:pass@127.0.0.1:1234",
    "http://127.0.0.1:1234?token=secret", "http://127.0.0.1", "https://example.com"
  ]) assert.throws(() => normalizeEndpoint(endpoint));
});

test("page hashes distinguish query-identified pages and omit credentials/fragments", async () => {
  const first = await describeTab(tab());
  const other = await describeTab(tab({url: "https://www.youtube.com/watch?v=video-two"}));
  assert.notEqual(first.page_key, other.page_key);
  const fragment = await describeTab(tab({url: "https://user:password@www.youtube.com/watch?v=video-one&secret=local-only#different"}));
  assert.equal(first.page_key, fragment.page_key);
  assert.equal(first.title, "");
  assert.equal(first.title_key, await digest("a helpful tutorial"));
  assert.equal(first.domain, "www.youtube.com");
  const serialized = JSON.stringify(first);
  for (const raw of ["watch", "video-one", "local-only", "password", "chapter"]) {
    assert.equal(serialized.includes(raw), false);
  }
});

test("private, internal, and file tabs are excluded before description", async () => {
  assert.equal(await describeTab(tab({incognito: true})), null);
  assert.equal(await describeTab(tab({url: "chrome://settings"})), null);
  assert.equal(await describeTab(tab({url: "file:///home/user/secret.txt"})), null);
});

test("unpaired and paused profiles do not contact the bridge or inspect tabs", async () => {
  for (const paired of [false, true]) {
    const f = fixture({paired});
    if (paired) f.api.storage.local.data.enabled = false;
    await f.bridge.sync();
    assert.equal(f.requests.length, 0);
    assert.deepEqual(f.reads, {tabs: 0, windows: 0});
  }
});

test("paired idle bridge receives no tab metadata and no tab queries", async () => {
  const f = fixture();
  await f.bridge.sync();
  assert.deepEqual(f.reads, {tabs: 0, windows: 0});
  assert.equal(f.posts().length, 1);
  const body = f.posts()[0].payload;
  assert.equal(body.focused, false);
  assert.equal(body.title, "");
  assert.equal(body.url, "");
  assert.equal(body.domain, "");
  assert.deepEqual(body.tabs, []);
});

test("active block receives a focused tab with default title suppression", async () => {
  const f = fixture({status: {active: true}});
  await f.bridge.sync();
  const post = f.posts()[0];
  assert.equal(post.headers.Authorization, "Bearer " + TOKEN);
  assert.equal(post.credentials, "omit");
  assert.equal(post.redirect, "error");
  assert.equal(post.payload.focused, true);
  assert.equal(post.payload.tab_id, 7);
  assert.equal(post.payload.window_id, 3);
  assert.equal(post.payload.domain, "www.youtube.com");
  assert.equal(post.payload.title, "");
  assert.equal(post.payload.url, "");
  assert.equal(post.payload.title_key.length, 64);
  assert.equal(post.payload.page_key.length, 64);
  assert.equal(post.payload.browser, "chrome");
  assert.equal(post.payload.incognito, false);
  assert.equal(typeof post.payload.sent_at, "number");
  assert.equal(JSON.stringify(post.payload).includes("video-one"), false);
});

test("title capture is a separate flag and inventory is independently gated", async () => {
  const active = fixture({status: {active: true, include_titles: true}});
  await active.bridge.sync();
  assert.equal(active.posts()[0].payload.title, "A helpful tutorial");
  const inventory = fixture({
    status: {inventory_requested: true},
    tabs: [tab(), tab({id: 8, incognito: true, title: "private title"}), tab({id: 9, url: "chrome://settings"})]
  });
  await inventory.bridge.sync();
  const body = inventory.posts()[0].payload;
  assert.equal(body.focused, false);
  assert.equal(body.tabs.length, 1);
  assert.equal(body.tabs[0].title, "A helpful tutorial");
  assert.equal(JSON.stringify(body).includes("private title"), false);
  assert.equal(body.tabs[0].page_key.length, 64);
});

test("background Chrome and private windows cannot report foreground tab time", async () => {
  for (const window of [{focused: false}, {incognito: true}, {type: "popup"}]) {
    const f = fixture({status: {active: true, include_titles: true}, window});
    await f.bridge.sync();
    assert.equal(f.posts()[0].payload.focused, false);
    assert.equal(f.posts()[0].payload.title, "");
    assert.equal(f.reads.tabs, 0);
  }
});

test("focus lost event sends an empty false heartbeat without a status round trip", async () => {
  const f = fixture({status: {active: true}});
  f.bridge.bindEvents();
  f.api.windows.onFocusChanged.fire(-1);
  await new Promise((resolve) => setTimeout(resolve, 10));
  clearTimeout(f.bridge.eventTimer);
  assert.equal(f.requests.length, 1);
  assert.equal(f.requests[0].payload.focused, false);
  assert.deepEqual(f.reads, {tabs: 0, windows: 0});
});

test("pairing must verify bridge identity before storing a token", async () => {
  const f = fixture({paired: false});
  const response = await f.bridge.handleMessage({type: "pair", endpoint: ENDPOINT, token: TOKEN});
  assert.equal(response.ok, true);
  assert.equal(f.api.storage.local.data.token, TOKEN);
  assert.equal(f.api.alarms.created[0][1].periodInMinutes, 0.5);
  assert.equal("token" in response.state, false);
  const wrong = fixture({paired: false, status: {pairing: false}});
  const rejected = await wrong.bridge.handleMessage({type: "pair", endpoint: ENDPOINT, token: TOKEN});
  assert.equal(rejected.ok, false);
  assert.equal(wrong.api.storage.local.data.token, undefined);
  assert.equal(rejected.error.includes(TOKEN), false);
});

test("stop clears foreground context; disconnect removes the stored token", async () => {
  const f = fixture({status: {active: true}});
  await f.bridge.sync();
  const identities = await f.bridge.identities;
  await f.bridge.setEnabled(false);
  assert.equal(f.posts().at(-1).payload.focused, false);
  assert.equal(f.api.storage.local.data.enabled, false);
  const count = f.requests.length;
  await f.bridge.sync();
  assert.equal(f.requests.length, count);
  await f.bridge.disconnect();
  assert.equal(f.api.storage.local.data.token, undefined);
  assert.equal(f.api.storage.local.data.endpoint, undefined);
  assert.equal(f.api.storage.local.data.profile_id, identities.profile_id);
  assert.equal((await f.bridge.state()).paired, false);
});

test("stop during a pending status request prevents later metadata reads", async () => {
  const f = fixture({status: {active: true}});
  let releaseStatus;
  let statusStarted;
  const started = new Promise((resolve) => { statusStarted = resolve; });
  f.bridge.fetchImpl = async (url) => {
    if (url.endsWith("/v1/status")) {
      statusStarted();
      await new Promise((resolve) => { releaseStatus = resolve; });
      return {ok: true, json: async () => ({pairing: true, active: true, inventory_requested: false})};
    }
    return {ok: true};
  };
  const sync = f.bridge.sync();
  await started;
  await f.bridge.setEnabled(false);
  releaseStatus();
  await sync;
  assert.deepEqual(f.reads, {tabs: 0, windows: 0});
});

test("profile identity persists while browser instance identity changes on restart", async () => {
  const first = fixture();
  const ids = await first.bridge.identities;
  const workerRestart = fixture({local: first.api.storage.local.data, session: first.api.storage.session.data});
  assert.deepEqual(await workerRestart.bridge.identities, ids);
  const browserRestart = fixture({local: first.api.storage.local.data, session: {}});
  const newIds = await browserRestart.bridge.identities;
  assert.equal(newIds.profile_id, ids.profile_id);
  assert.notEqual(newIds.browser_instance_id, ids.browser_instance_id);
});

test("inventory caps bound payload size without sending raw URLs", async () => {
  const tabs = Array.from({length: 500}, (_, index) => tab({
    id: index, title: "Long tab title ".repeat(50), url: "https://example.com/page?item=" + index
  }));
  const f = fixture({status: {inventory_requested: true}, tabs});
  await f.bridge.sync();
  const payload = f.posts()[0].payload;
  assert.equal(payload.inventory_truncated, true);
  assert.ok(payload.tabs.length <= 256);
  assert.ok(new TextEncoder().encode(JSON.stringify(payload)).length < 48000);
  assert.equal(JSON.stringify(payload).includes("?item="), false);
});

const timer = (changes = {}) => ({
  status: "running", session_id: 7, name: "calm-otter", remaining_seconds: 1200,
  kind: "focus", can_control: true, ui_theme: "midnight", revision: 3, ...changes
});

test("timer status exposes safe theme fields and correct primary actions", () => {
  for (const ui_theme of ["midnight", "gameboy", "sunset"]) {
    assert.equal(normalizeTimer(timer({ui_theme})).ui_theme, ui_theme);
  }
  assert.equal(normalizeTimer(timer({ui_theme: "unknown"})).ui_theme, "midnight");
  assert.equal(timerPrimaryAction(timer()), "pause");
  assert.equal(timerPrimaryAction(timer({status: "paused"})), "resume");
  assert.equal(timerPrimaryAction(timer({status: "ready", session_id: null})), "start");
  assert.equal(timerPrimaryAction(timer({status: "finished"})), null);
  assert.equal(normalizeTimer(timer({session_id: null})), null);
  assert.equal(normalizeTimer(timer({revision: 1.5})), null);
  assert.equal(normalizeTimer(timer({remaining_seconds: NaN})), null);
  assert.equal(normalizeTimer(undefined), null);
  assert.equal(formatRemaining(1500), "25:00");
  assert.equal(formatRemaining(0.2), "00:01");
  assert.equal(formatRemaining(3600), "01:00:00");
});

test("session controls bind to the displayed ID/revision and use the control endpoint", async () => {
  for (const [action, status, session_id] of [
    ["start", "ready", null], ["pause", "running", 7], ["resume", "paused", 7], ["finish", "running", 7]
  ]) {
    const f = fixture({status: {timer: timer({status, session_id, ui_theme: "sunset"})}});
    f.bridge.serverStatus = structuredClone(f.remoteStatus);
    f.bridge.connectionState = "connected";
    const result = await f.bridge.handleMessage({type: "timer-control", action, session_id, revision: 3});
    assert.equal(result.ok, true);
    assert.equal(result.accepted, true);
    const controls = f.requests.filter((request) => request.url.endsWith("/v1/control"));
    assert.equal(controls.length, 1);
    assert.equal(controls[0].method, "POST");
    assert.equal(controls[0].headers.Authorization, "Bearer " + TOKEN);
    assert.deepEqual(controls[0].payload, {action, session_id, revision: 3});
    assert.equal(result.state.timer.ui_theme, "sunset");
    assert.deepEqual(f.reads, {tabs: 0, windows: 0});
  }
});

test("stopped browser sharing still permits timer status and controls without tab reads", async () => {
  const f = fixture({status: {timer: timer({ui_theme: "gameboy"})}});
  f.api.storage.local.data.enabled = false;
  const state = await f.bridge.handleMessage({type: "get-state"});
  assert.equal(state.state.enabled, false);
  assert.equal(state.state.timer.ui_theme, "gameboy");
  assert.equal(state.state.timer.status, "running");
  const controlled = await f.bridge.handleMessage({type: "timer-control", action: "pause", session_id: 7, revision: 3});
  assert.equal(controlled.ok, true);
  assert.equal(f.api.storage.local.data.enabled, false);
  assert.ok(f.requests.every((request) => !request.url.endsWith("/v1/browser")));
  assert.deepEqual(f.reads, {tabs: 0, windows: 0});
});

test("stale or mismatched commands are not silently rebound to another timer", async () => {
  for (const binding of [{session_id: 8, revision: 3}, {session_id: 7, revision: 2}]) {
    const f = fixture({status: {timer: timer()}});
    f.bridge.serverStatus = structuredClone(f.remoteStatus);
    f.bridge.connectionState = "connected";
    const result = await f.bridge.handleMessage({type: "timer-control", action: "pause", ...binding});
    assert.equal(result.ok, false);
    assert.match(result.error, /timer changed or is busy/);
    assert.equal(f.requests.filter((request) => request.url.endsWith("/v1/control")).length, 0);
  }
});

test("server 409 refreshes the timer but never retries the command", async () => {
  const f = fixture({status: {timer: timer()}});
  f.bridge.serverStatus = structuredClone(f.remoteStatus);
  f.bridge.connectionState = "connected";
  f.bridge.fetchImpl = async (url, options) => {
    f.requests.push({url, ...options, payload: options.body ? JSON.parse(options.body) : null});
    if (url.endsWith("/v1/control")) {
      f.remoteStatus.timer = timer({status: "paused", revision: 4});
      return {ok: false, status: 409};
    }
    return {ok: true, status: 200, json: async () => f.remoteStatus};
  };
  const result = await f.bridge.handleMessage({type: "timer-control", action: "pause", session_id: 7, revision: 3});
  assert.equal(result.ok, false);
  assert.match(result.error, /timer changed or is busy/);
  assert.equal(result.state.timer.revision, 4);
  assert.equal(f.requests.filter((request) => request.url.endsWith("/v1/control")).length, 1);
});

test("busy or older timers and unsupported actions never enqueue controls", async () => {
  for (const snapshot of [undefined, timer({can_control: false})]) {
    const f = fixture({status: {timer: snapshot}});
    f.bridge.serverStatus = structuredClone(f.remoteStatus);
    f.bridge.connectionState = "connected";
    const result = await f.bridge.handleMessage({type: "timer-control", action: "finish", session_id: 7, revision: 3});
    assert.equal(result.ok, false);
    assert.equal(f.requests.filter((request) => request.url.endsWith("/v1/control")).length, 0);
  }
  const f = fixture({status: {timer: timer()}});
  f.bridge.serverStatus = structuredClone(f.remoteStatus);
  f.bridge.connectionState = "connected";
  const result = await f.bridge.handleMessage({type: "timer-control", action: "reset", session_id: 7, revision: 3});
  assert.equal(result.ok, false);
  assert.equal(f.requests.filter((request) => request.url.endsWith("/v1/control")).length, 0);
});

test("a control response must be queued with 202, not inferred as applied from 200", async () => {
  const f = fixture({status: {timer: timer()}});
  f.bridge.serverStatus = structuredClone(f.remoteStatus);
  f.bridge.connectionState = "connected";
  f.bridge.fetchImpl = async (url, options) => {
    f.requests.push({url, ...options, payload: options.body ? JSON.parse(options.body) : null});
    return {ok: true, status: 200, json: async () => f.remoteStatus};
  };
  const result = await f.bridge.handleMessage({type: "timer-control", action: "pause", session_id: 7, revision: 3});
  assert.equal(result.ok, false);
  assert.match(result.error, /did not accept/);
});

test("popup immediately reads an already-running timer without waiting for tab collection", async () => {
  const f = fixture({status: {active: true, timer: timer({name: "already-running", revision: 8})}});
  let tabStarted;
  let releaseTab;
  const started = new Promise((resolve) => { tabStarted = resolve; });
  f.api.tabs.query = async () => {
    tabStarted();
    return new Promise((resolve) => { releaseTab = resolve; });
  };
  const collection = f.bridge.sync();
  await started;
  let timeout;
  try {
    const response = await Promise.race([
      f.bridge.handleMessage({type: "get-state"}),
      new Promise((_resolve, reject) => { timeout = setTimeout(() => reject(new Error("Timer waited for tab collection")), 500); })
    ]);
    assert.equal(response.state.timer.name, "already-running");
    assert.equal(response.state.timer.status, "running");
    assert.equal(response.state.timer.revision, 8);
    assert.equal(response.state.timer_stale, false);
    assert.equal(f.api.storage.local.data.enabled, true);
  } finally {
    clearTimeout(timeout);
    releaseTab([tab()]);
    await collection;
  }
});

test("worker startup and restart pick up a running session even with sharing stopped", async () => {
  const f = fixture({status: {timer: timer({name: "from-tui", revision: 11})}});
  f.api.storage.local.data.enabled = false;
  await f.bridge.initialize();
  let state = await f.bridge.state();
  assert.equal(state.timer.name, "from-tui");
  assert.equal(state.timer.status, "running");
  assert.equal(state.enabled, false);
  f.remoteStatus.timer = timer({name: "new-current-block", session_id: 9, revision: 12});
  const restarted = new BrowserBridge(f.api, f.bridge.fetchImpl);
  await restarted.initialize();
  state = await restarted.state();
  assert.equal(state.timer.session_id, 9);
  assert.equal(state.timer.name, "new-current-block");
  assert.equal(state.enabled, false);
  assert.deepEqual(f.reads, {tabs: 0, windows: 0});
  assert.ok(f.requests.every((request) => request.url.endsWith("/v1/status")));
});

test("tab event churn cannot discard a successful timer status", async () => {
  const f = fixture({status: {active: true, timer: timer({revision: 13})}});
  f.bridge.status = async () => {
    f.bridge.eventRevision += 1;
    return f.remoteStatus;
  };
  await f.bridge.sync();
  const state = await f.bridge.state();
  assert.equal(state.timer.revision, 13);
  assert.equal(state.connection_state, "connected");
  assert.equal(f.posts().length, 0);
});

test("tab query and browser-post failures do not erase a fresh timer", async () => {
  for (const failure of ["tabs", "post"]) {
    const f = fixture({status: {active: true, timer: timer({name: "still-running", revision: 14})}});
    if (failure === "tabs") {
      f.api.tabs.query = async () => { throw new Error("Tab unavailable"); };
    } else {
      const original = f.bridge.fetchImpl;
      f.bridge.fetchImpl = async (url, options) => url.endsWith("/v1/browser") ?
        {ok: false, status: 500} : original(url, options);
    }
    await f.bridge.sync();
    const response = await f.bridge.handleMessage({type: "get-state"});
    assert.equal(response.state.timer.name, "still-running");
    assert.equal(response.state.timer.status, "running");
    assert.equal(response.state.timer_stale, false);
    assert.equal(response.state.connection_state, "connected");
    assert.equal(response.state.browser_state, "unavailable");
  }
});

test("older ready response cannot overwrite a newer running status", async () => {
  const f = fixture();
  const pending = [];
  f.bridge.status = async () => new Promise((resolve) => pending.push(resolve));
  const first = f.bridge.refreshStatus();
  await new Promise((resolve) => setTimeout(resolve, 0));
  const second = f.bridge.refreshStatus();
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(pending.length, 2);
  pending[1]({...f.remoteStatus, timer: timer({name: "newer-running", revision: 20})});
  await second;
  pending[0]({...f.remoteStatus, timer: timer({status: "ready", session_id: null, name: "old-ready", revision: 1})});
  await first;
  assert.equal((await f.bridge.state()).timer.name, "newer-running");
});

test("failed or aged status retains the last identity but disables stale timer control", async () => {
  const f = fixture({status: {timer: timer({name: "last-known"})}});
  await f.bridge.refreshStatus();
  f.bridge.lastStatusAt = performance.now() - 16000;
  assert.equal((await f.bridge.state()).timer_stale, true);
  f.bridge.fetchImpl = async () => { throw new Error("Server unavailable"); };
  await f.bridge.refreshStatus();
  const state = await f.bridge.state();
  assert.equal(state.timer.name, "last-known");
  assert.equal(state.timer_stale, true);
  assert.equal(state.connection_state, "unavailable");
  const response = await f.bridge.handleMessage({type: "timer-control", action: "pause", session_id: 7, revision: 3});
  assert.equal(response.ok, false);
});

test("TUI start discovered by popup status prompts capture without a tab activation event", async () => {
  const f = fixture({status: {timer: timer({status: "ready", session_id: null})}});
  await f.bridge.handleMessage({type: "get-state"});
  assert.equal(f.reads.tabs, 0);
  f.remoteStatus.active = true;
  f.remoteStatus.timer = timer({name: "started-in-tui", revision: 4});
  const response = await f.bridge.handleMessage({type: "get-state"});
  assert.equal(response.state.timer.name, "started-in-tui");
  if (f.bridge.syncing) await f.bridge.syncing;
  assert.ok(f.posts().some((post) => post.payload.focused && post.payload.domain === "www.youtube.com"));
  assert.equal(f.api.storage.local.data.enabled, true);
});

test("status body parsing remains bounded after response headers", async () => {
  const f = fixture();
  f.bridge.requestTimeoutMs = 20;
  f.bridge.fetchImpl = async (_url, options) => ({ok: true, json: () => new Promise((_resolve, reject) => {
    options.signal.addEventListener("abort", () => reject(new Error("aborted body")), {once: true});
  })});
  await f.bridge.refreshStatus();
  assert.equal(f.bridge.connectionState, "unavailable");
});

test("late focus-loss failure cannot overwrite a newer successful browser report", async () => {
  const f = fixture({status: {active: true}});
  let rejectOld;
  const original = f.bridge.fetchImpl;
  f.bridge.fetchImpl = async (url, options) => {
    if (url.endsWith("/v1/browser") && !JSON.parse(options.body).focused) {
      return new Promise((_resolve, reject) => { rejectOld = reject; });
    }
    return original(url, options);
  };
  f.bridge.forceUnfocused = true;
  const old = f.bridge.reportUnfocused();
  while (!rejectOld) await new Promise(resolve => setTimeout(resolve, 0));
  f.bridge.forceUnfocused = false;
  await f.bridge.sync();
  assert.equal(f.bridge.browserState, "connected");
  rejectOld(new Error("old network failure"));
  await old;
  assert.equal(f.bridge.browserState, "connected");
});

test("late status failure cannot mark a newer session snapshot unavailable", async () => {
  const f = fixture();
  const pending = [];
  f.bridge.status = () => new Promise((resolve, reject) => pending.push({resolve, reject}));
  const old = f.bridge.refreshStatus();
  while (pending.length < 1) await new Promise(resolve => setTimeout(resolve, 0));
  const newer = f.bridge.refreshStatus();
  while (pending.length < 2) await new Promise(resolve => setTimeout(resolve, 0));
  pending[1].resolve({...f.remoteStatus, timer: timer({revision: 33, name: "current"})});
  await newer;
  pending[0].reject(new Error("old connection"));
  await old;
  assert.equal((await f.bridge.state()).timer.name, "current");
  assert.equal(f.bridge.connectionState, "connected");
});
