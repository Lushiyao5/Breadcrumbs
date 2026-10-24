import {formatRemaining, timerPrimaryAction} from "./core.mjs";

const element = (id) => document.getElementById(id);
let busy = false;
let currentState = null;
let timerSampleAt = 0;
let finishBinding = null;
let pendingTimer = null;
let pairingInitialized = false;

function timerAvailable(state) {
  return Boolean(state && state.paired && state.timer && !state.timer_stale &&
    state.connection_state !== "unavailable" && performance.now() - timerSampleAt <= 15000);
}

function updateClock() {
  if (!timerAvailable(currentState)) {
    element("timer-clock").textContent = "--:--";
    element("timer-primary").disabled = true;
    element("timer-finish").disabled = true;
    element("timer-confirm").disabled = true;
    element("timer-state").textContent = "OFFLINE";
    if (currentState?.paired && currentState.timer && performance.now() - timerSampleAt > 15000) {
      element("timer-detail").textContent = "Waiting for a fresh timer update from Breadcrumbs…";
    }
    return;
  }
  const timer = currentState.timer;
  const elapsed = timer.status === "running" ? (performance.now() - timerSampleAt) / 1000 : 0;
  element("timer-clock").textContent = formatRemaining(Math.max(0, timer.remaining_seconds - elapsed));
}

function paintTimer(state) {
  const timer = state.timer;
  const available = timerAvailable(state);
  const badge = element("timer-state");
  element("session-panel").hidden = !state.paired;
  document.body.dataset.theme = timer ? timer.ui_theme : "midnight";
  badge.textContent = available ? timer.status.toUpperCase() : "OFFLINE";
  badge.dataset.state = available ? timer.status : "offline";
  element("timer-name").textContent = timer && timer.name ? timer.name : "No session available";
  element("timer-kind").textContent = timer ? ({
    focus: "Focus", short_break: "Short break", long_break: "Long break", custom: "Custom timer"
  })[timer.kind] : "Breadcrumbs";

  if (finishBinding && (!available || finishBinding.session_id !== timer.session_id ||
      finishBinding.revision !== timer.revision || !timer.can_control ||
      !["running", "paused"].includes(timer.status))) {
    finishBinding = null;
  }
  if (pendingTimer) {
    if (!available || timer.session_id !== pendingTimer.session_id || timer.revision !== pendingTimer.revision) {
      pendingTimer = null;
    } else if (performance.now() - pendingTimer.started > 15000) {
      pendingTimer = null;
      element("error").textContent = "The timer command has not been confirmed. Check Breadcrumbs before trying again.";
    }
  }
  const primary = available ? timerPrimaryAction(timer) : null;
  const canControl = available && timer.can_control && !busy && !pendingTimer;
  element("timer-primary").textContent = primary ? primary[0].toUpperCase() + primary.slice(1) : "Start";
  element("timer-primary").disabled = !canControl || !primary || Boolean(finishBinding);
  element("timer-finish").disabled = !canControl || !["running", "paused"].includes(timer?.status);
  element("timer-finish").hidden = Boolean(available && !["running", "paused"].includes(timer.status));
  element("timer-confirmation").hidden = !finishBinding;
  element("timer-confirm").disabled = !canControl || !finishBinding;
  element("timer-cancel").disabled = busy;
  element("timer-confirm-name").textContent = finishBinding ? finishBinding.name : "";

  let detail;
  if (!available) detail = "Keep Breadcrumbs open to control the timer. Older versions may need an update.";
  else if (pendingTimer) detail = "Command accepted. Waiting for Breadcrumbs to confirm the change…";
  else if (!timer.can_control) detail = "The timer is busy in Breadcrumbs. Finish or close the open dialog there.";
  else if (timer.status === "ready") detail = "Start uses your last approved scope. With no scope, the block is untracked.";
  else if (timer.status === "paused") detail = "Resume continues this same block.";
  else if (timer.status === "finished") detail = "Complete the reflection in Breadcrumbs to continue.";
  else detail = "Timer controls and browser sharing are independent.";
  element("timer-detail").textContent = detail;
  updateClock();
}

function paint(state, fresh = true) {
  if (fresh) {
    currentState = state;
    timerSampleAt = performance.now();
  }
  const status = element("status");
  status.dataset.state = state.connection_state;
  if (!state.paired) {
    status.textContent = "Not paired";
    element("detail").textContent = "Copy the connection URL and token shown by Breadcrumbs.";
  } else if (!state.enabled) {
    status.textContent = "Sharing stopped";
    element("detail").textContent = "Tab details are not shared. You can still control the timer above.";
  } else if (state.connection_state === "unavailable") {
    status.textContent = "Waiting for Breadcrumbs";
    element("detail").textContent = "Keep Breadcrumbs open. The saved connection reconnects automatically.";
  } else if (state.browser_state === "unavailable") {
    status.textContent = "Tab context unavailable";
    element("detail").textContent = "The timer is connected. Browser context will retry separately.";
  } else if (state.inventory_requested) {
    status.textContent = "Scope picker connected";
    element("detail").textContent = "Normal web tabs are shared while you choose the scope in Breadcrumbs.";
  } else if (state.active) {
    status.textContent = "Focus context connected";
    const tab = state.tab_context;
    element("detail").textContent = tab ?
      ((tab.title || tab.domain) + " · " + tab.domain + (tab.title_shared ? "" : " · title sharing is off")) :
      "Waiting for a focused web tab. Check sharing, site permissions, and that the page is not private/internal.";
  } else {
    status.textContent = "Paired · ready";
    element("detail").textContent = "No tab details are shared until a tracked block runs or the scope picker requests them.";
  }
  const settings = element("connection-settings");
  if (!pairingInitialized || !state.paired) {
    settings.open = !state.paired;
    pairingInitialized = true;
  }
  if (!element("endpoint").value && state.endpoint) element("endpoint").value = state.endpoint;
  element("start").disabled = busy || !state.paired || state.enabled;
  element("stop").disabled = busy || !state.paired || !state.enabled;
  element("disconnect").disabled = busy || !state.paired;
  element("pair").disabled = busy;
  paintTimer(state);
}

async function send(message) {
  try {
    const response = await chrome.runtime.sendMessage(message);
    if (!response) throw new Error("No response");
    if (response.state) paint(response.state);
    if (!response.ok) element("error").textContent = response.error || "Could not connect. Keep Breadcrumbs open and try again.";
    return response;
  } catch {
    element("error").textContent = "The extension could not respond. Reload it from Chrome's Extensions page.";
    return {ok: false};
  }
}

async function command(message) {
  busy = true;
  element("error").textContent = "";
  if (currentState) paint(currentState, false);
  try {
    return await send(message);
  } finally {
    busy = false;
    if (currentState) paint(currentState, false);
  }
}

async function controlTimer(action, binding) {
  if (busy || pendingTimer) return;
  finishBinding = null;
  const response = await command({
    type: "timer-control", action,
    session_id: binding.session_id, revision: binding.revision
  });
  if (response.ok && response.accepted) {
    pendingTimer = {...binding, started: performance.now()};
  }
  if (currentState) paint(currentState, false);
}

element("timer-primary").addEventListener("click", () => {
  const timer = currentState?.timer;
  const action = timerPrimaryAction(timer);
  if (timerAvailable(currentState) && timer.can_control && action) {
    void controlTimer(action, {session_id: timer.session_id, revision: timer.revision});
  }
});
element("timer-finish").addEventListener("click", () => {
  const timer = currentState?.timer;
  if (!timerAvailable(currentState) || !timer.can_control || !["running", "paused"].includes(timer.status)) return;
  finishBinding = {session_id: timer.session_id, revision: timer.revision, name: timer.name};
  paint(currentState, false);
  element("timer-confirm").focus();
});
element("timer-confirm").addEventListener("click", () => {
  if (finishBinding) void controlTimer("finish", {...finishBinding});
});
element("timer-cancel").addEventListener("click", () => {
  finishBinding = null;
  if (currentState) paint(currentState, false);
  element("timer-finish").focus();
});
element("pair-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await command({
    type: "pair",
    endpoint: element("endpoint").value,
    token: element("token").value
  });
  if (response.ok) {
    element("token").value = "";
    element("connection-settings").open = false;
  }
});
element("start").addEventListener("click", () => void command({type: "start"}));
element("stop").addEventListener("click", () => void command({type: "stop"}));
element("disconnect").addEventListener("click", async () => {
  const response = await command({type: "disconnect"});
  if (response.ok) {
    element("token").value = "";
    element("endpoint").value = "";
    finishBinding = null;
    pendingTimer = null;
  }
});
element("open-options")?.addEventListener("click", () => void chrome.runtime.openOptionsPage());
void send({type: "get-state"});
setInterval(updateClock, 1000);
setInterval(() => { if (!busy) void send({type: "get-state"}); }, 4000);
document.addEventListener?.("visibilitychange", () => {
  if (document.visibilityState === "visible" && !busy) void send({type: "get-state"});
});
globalThis.addEventListener?.("focus", () => { if (!busy) void send({type: "get-state"}); });
