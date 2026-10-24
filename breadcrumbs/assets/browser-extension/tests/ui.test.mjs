import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import {formatRemaining, timerPrimaryAction} from "../core.mjs";

const source = fs.readFileSync(new URL("../connection.js", import.meta.url), "utf8")
  .replace(/^import[^\n]+\n/, "");
const markup = fs.readFileSync(new URL("../popup.html", import.meta.url), "utf8");

function uiFixture(initialTimer = {}) {
  const nodes = new Map(Array.from(markup.matchAll(/id="([^"]+)"/g), (match) => [
    match[1], {
      textContent: "", value: "", disabled: false, hidden: false, open: false,
      dataset: {}, listeners: new Map(),
      addEventListener(type, callback) { this.listeners.set(type, callback); },
      focus() { this.focused = true; }
    }
  ]));
  const state = {
    paired: true, enabled: true, endpoint: "http://127.0.0.1:43127",
    connection_state: "connected", active: true, inventory_requested: false,
    timer: {status: "running", session_id: 7, name: "calm-otter", remaining_seconds: 1200,
      kind: "focus", can_control: true, ui_theme: "midnight", revision: 3, ...initialTimer}
  };
  const messages = [];
  const intervals = [];
  let now = 0;
  const documentEvents = new Map();
  const windowEvents = new Map();
  const document = {
    body: {dataset: {}}, visibilityState: "visible",
    getElementById: (id) => nodes.get(id) || null,
    addEventListener: (type, callback) => documentEvents.set(type, callback)
  };
  const context = vm.createContext({
    document, formatRemaining, timerPrimaryAction,
    performance: {now: () => now},
    addEventListener: (type, callback) => windowEvents.set(type, callback),
    setInterval: (callback, delay) => { intervals.push({callback, delay}); return intervals.length; },
    chrome: {runtime: {
      async sendMessage(message) {
        messages.push(JSON.parse(JSON.stringify(message)));
        if (message.type === "stop") state.enabled = false;
        if (message.type === "start") state.enabled = true;
        if (message.type === "timer-control") {
          state.timer.revision += 1;
          state.timer.status = ({pause: "paused", resume: "running", start: "running", finish: "finished"})[message.action];
          if (message.action === "finish") state.timer.can_control = false;
          return {ok: true, accepted: true, state: structuredClone(state)};
        }
        return {ok: true, state: structuredClone(state)};
      },
      async openOptionsPage() {}
    }}
  });
  vm.runInContext(source, context);
  return {
    nodes, state, messages, document, intervals,
    now: (value) => { now = value; },
    click: (id) => nodes.get(id).listeners.get("click")(),
    poll: () => intervals.find((entry) => entry.delay === 4000).callback(),
    tick: () => intervals.find((entry) => entry.delay === 1000).callback(),
    visible: () => documentEvents.get("visibilitychange")(),
    focus: () => windowEvents.get("focus")()
  };
}
async function settle() {
  for (let i = 0; i < 8; i++) await Promise.resolve();
}

test("browser panel shows the actual reported tab and clears it when sharing stops", async () => {
  const ui = uiFixture();
  await settle();
  ui.state.tab_context = {title: "Python documentation", domain: "docs.python.org", title_shared: true};
  ui.poll();
  await settle();
  assert.match(ui.nodes.get("detail").textContent, /Python documentation/);
  assert.match(ui.nodes.get("detail").textContent, /docs.python.org/);
  ui.click("stop");
  await settle();
  assert.doesNotMatch(ui.nodes.get("detail").textContent, /Python documentation/);
  assert.match(ui.nodes.get("timer-name").textContent, /calm-otter/);
});

test("an extension build mismatch is actionable without disabling a healthy timer", async () => {
  const ui = uiFixture();
  await settle();
  ui.state.extension_update_required = true;
  ui.poll();
  await settle();
  assert.match(ui.nodes.get("build-status").textContent, /Reload this extension/);
  assert.equal(ui.nodes.get("timer-state").textContent, "RUNNING");
  assert.equal(ui.nodes.get("timer-primary").disabled, false);
});

test("Finish requires the inline second click and preserves its session binding", async () => {
  const ui = uiFixture();
  await settle();
  ui.click("timer-finish");
  assert.equal(ui.nodes.get("timer-confirmation").hidden, false);
  assert.equal(ui.messages.filter((message) => message.type === "timer-control").length, 0);
  ui.click("timer-confirm");
  await settle();
  assert.deepEqual(ui.messages.find((message) => message.type === "timer-control"), {
    type: "timer-control", action: "finish", session_id: 7, revision: 3
  });
  assert.equal(ui.nodes.get("timer-confirmation").hidden, true);
  assert.equal(ui.nodes.get("timer-state").textContent, "FINISHED");
});

test("changed session cancels an open Finish confirmation without retargeting it", async () => {
  const ui = uiFixture();
  await settle();
  ui.click("timer-finish");
  ui.state.timer.session_id = 8;
  ui.state.timer.revision = 4;
  ui.state.timer.name = "next-block";
  ui.poll();
  await settle();
  assert.equal(ui.nodes.get("timer-confirmation").hidden, true);
  ui.click("timer-confirm");
  await settle();
  assert.equal(ui.messages.filter((message) => message.type === "timer-control").length, 0);
});

test("Keep working cancels Finish and browser sharing remains independent", async () => {
  const ui = uiFixture();
  await settle();
  ui.click("timer-finish");
  ui.click("timer-cancel");
  assert.equal(ui.nodes.get("timer-confirmation").hidden, true);
  ui.click("stop");
  await settle();
  assert.equal(ui.state.enabled, false);
  assert.equal(ui.state.timer.status, "running");
  assert.equal(ui.nodes.get("timer-primary").textContent, "Pause");
  ui.click("timer-primary");
  await settle();
  const controls = ui.messages.filter((message) => message.type === "timer-control");
  assert.equal(controls.length, 1);
  assert.equal(controls[0].action, "pause");
  assert.equal(ui.state.enabled, false);
  assert.equal(ui.state.timer.status, "paused");
  assert.equal(ui.nodes.get("timer-primary").textContent, "Resume");
});

test("clock interpolates only while running and paired theme follows the TUI", async () => {
  const ui = uiFixture();
  await settle();
  assert.equal(ui.nodes.get("timer-clock").textContent, "20:00");
  ui.now(5000);
  ui.tick();
  assert.equal(ui.nodes.get("timer-clock").textContent, "19:55");
  ui.state.timer.status = "paused";
  ui.state.timer.remaining_seconds = 1195;
  ui.state.timer.ui_theme = "sunset";
  ui.poll();
  await settle();
  ui.now(10000);
  ui.tick();
  assert.equal(ui.nodes.get("timer-clock").textContent, "19:55");
  assert.equal(ui.document.body.dataset.theme, "sunset");
  ui.state.timer.ui_theme = "gameboy";
  ui.poll();
  await settle();
  assert.equal(ui.document.body.dataset.theme, "gameboy");
});

test("visible or reopened popup picks up an already-running TUI session without Start", async () => {
  const ui = uiFixture({status: "ready", session_id: null, name: "ready-block"});
  await settle();
  assert.equal(ui.nodes.get("timer-primary").textContent, "Start");
  Object.assign(ui.state.timer, {status: "running", session_id: 9, name: "started-in-tui", revision: 8});
  ui.visible();
  await settle();
  assert.equal(ui.nodes.get("timer-primary").textContent, "Pause");
  assert.equal(ui.nodes.get("timer-name").textContent, "started-in-tui");
  ui.state.timer.name = "recovered-in-tui";
  ui.state.timer.status = "paused";
  ui.state.timer.revision = 9;
  ui.focus();
  await settle();
  assert.equal(ui.nodes.get("timer-name").textContent, "recovered-in-tui");
  assert.equal(ui.nodes.get("timer-primary").textContent, "Resume");
  assert.equal(ui.messages.filter((message) => message.type === "timer-control").length, 0);
});

test("stale popup cannot keep extrapolating or controlling its last good snapshot", async () => {
  const ui = uiFixture();
  await settle();
  ui.now(16000);
  ui.tick();
  assert.equal(ui.nodes.get("timer-clock").textContent, "--:--");
  assert.equal(ui.nodes.get("timer-primary").disabled, true);
  assert.equal(ui.nodes.get("timer-finish").disabled, true);
  assert.equal(ui.nodes.get("timer-state").textContent, "OFFLINE");
  ui.focus();
  await settle();
  assert.equal(ui.nodes.get("timer-clock").textContent, "20:00");
  assert.equal(ui.nodes.get("timer-primary").disabled, false);
});

test("rapid primary and Finish confirmation double clicks enqueue one command", async () => {
  for (const finish of [false, true]) {
    const ui = uiFixture();
    await settle();
    if (finish) ui.click("timer-finish");
    const target = finish ? "timer-confirm" : "timer-primary";
    const first = ui.click(target);
    const duplicate = ui.click(target);
    await Promise.all([first, duplicate]);
    await settle();
    assert.equal(ui.messages.filter(message => message.type === "timer-control").length, 1);
  }
});
