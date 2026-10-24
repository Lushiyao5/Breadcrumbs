import {describeTab, normalizeEndpoint, normalizeTimer, timerPrimaryAction} from "./core.mjs";

const HEARTBEAT_ALARM = "breadcrumbs-browser-heartbeat";
const PUBLIC_ERROR = "Could not reach Breadcrumbs. Check the connection URL and token, and keep Breadcrumbs open.";
const CONTROL_CONFLICT = "The timer changed or is busy. Review the current session and try again.";
const CONTROL_UNAVAILABLE = "Timer controls are unavailable. Keep Breadcrumbs open and close any dialog there.";

export class BrowserBridge {
  constructor(api, fetchImpl = (...args) => globalThis.fetch(...args)) {
    this.api = api;
    this.fetchImpl = fetchImpl;
    this.generation = 0;
    this.eventRevision = 0;
    this.forceUnfocused = false;
    this.serverStatus = null;
    this.connectionState = "not_paired";
    this.browserState = "idle";
    this.lastContact = null;
    this.lastStatusAt = null;
    this.statusSequence = 0;
    this.settledStatusSequence = 0;
    this.browserSequence = 0;
    this.settledBrowserSequence = 0;
    this.requestTimeoutMs = 2500;
    this.pending = false;
    this.syncing = null;
    this.eventTimer = null;
    this.interval = null;
    this.started = false;
    this.tabContext = null;
    this.tabContextAt = null;
    this.identities = this.ensureIdentities();
  }

  async ensureIdentities() {
    const local = await this.api.storage.local.get(["profile_id"]);
    const session = await this.api.storage.session.get(["browser_instance_id"]);
    const profileId = local.profile_id || crypto.randomUUID();
    const instanceId = session.browser_instance_id || crypto.randomUUID();
    if (!local.profile_id) await this.api.storage.local.set({profile_id: profileId});
    if (!session.browser_instance_id) {
      await this.api.storage.session.set({browser_instance_id: instanceId});
    }
    return {profile_id: profileId, browser_instance_id: instanceId};
  }

  async config() {
    const stored = await this.api.storage.local.get(["endpoint", "token", "enabled"]);
    if (!stored.endpoint || !stored.token) return null;
    try {
      return {endpoint: normalizeEndpoint(stored.endpoint), token: stored.token, enabled: stored.enabled === true};
    } catch {
      return null;
    }
  }

  async request(config, path, body, readJson = false) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.requestTimeoutMs);
    try {
      const headers = {Authorization: "Bearer " + config.token};
      if (body) headers["Content-Type"] = "application/json";
      const response = await this.fetchImpl(config.endpoint + path, {
        method: body ? "POST" : "GET",
        headers,
        body: body ? JSON.stringify(body) : undefined,
        cache: "no-store",
        credentials: "omit",
        redirect: "error",
        signal: controller.signal
      });
      if (!response.ok) {
        if (path === "/v1/control" && response.status === 409) throw new Error(CONTROL_CONFLICT);
        if (path === "/v1/control" && response.status === 404) throw new Error(CONTROL_UNAVAILABLE);
        throw new Error(PUBLIC_ERROR);
      }
      return readJson ? await response.json() : response;
    } finally {
      clearTimeout(timeout);
    }
  }

  async status(config) {
    const status = await this.request(config, "/v1/status", undefined, true);
    if (!status || status.pairing !== true ||
        typeof status.active !== "boolean" || typeof status.inventory_requested !== "boolean") {
      throw new Error(PUBLIC_ERROR);
    }
    return status;
  }

  async refreshStatus() {
    const generation = this.generation;
    const config = await this.config();
    if (!config) {
      this.serverStatus = null;
      this.connectionState = "not_paired";
      return;
    }
    const sequence = ++this.statusSequence;
    try {
      const status = await this.status(config);
      this.acceptStatus(status, config, generation, sequence);
    } catch {
      this.rejectStatus(generation, sequence);
    }
  }

  acceptStatus(status, config, generation, sequence) {
    if (generation !== this.generation || sequence < this.settledStatusSequence) return false;
    this.settledStatusSequence = sequence;
    this.serverStatus = status;
    this.connectionState = config.enabled ? "connected" : "paused";
    this.lastContact = Date.now() / 1000;
    this.lastStatusAt = performance.now();
    return true;
  }

  rejectStatus(generation, sequence) {
    if (generation !== this.generation || sequence < this.settledStatusSequence) return;
    this.settledStatusSequence = sequence;
    this.connectionState = "unavailable";
    // Retain the last good identity/theme for display, but never allow stale
    // status to control or extrapolate a live timer.
  }

  timerStale() {
    return this.connectionState === "unavailable" ||
      (this.lastStatusAt !== null && performance.now() - this.lastStatusAt > 15000);
  }

  async control(action, sessionId, revision) {
    const config = await this.config();
    if (!config) throw new Error("Pair this browser with Breadcrumbs first.");
    const timer = normalizeTimer(this.serverStatus && this.serverStatus.timer);
    if (!timer || !timer.can_control || this.timerStale()) {
      throw new Error(CONTROL_UNAVAILABLE);
    }
    if (!["start", "pause", "resume", "finish"].includes(action) ||
        !(sessionId === null || (Number.isSafeInteger(sessionId) && sessionId > 0)) ||
        !Number.isSafeInteger(revision) || revision < 0) {
      throw new Error("Invalid timer command.");
    }
    if (sessionId !== timer.session_id || revision !== timer.revision) throw new Error(CONTROL_CONFLICT);
    const allowed = action === "finish" ? ["running", "paused"].includes(timer.status) :
      action === timerPrimaryAction(timer);
    if (!allowed) throw new Error(CONTROL_CONFLICT);
    const response = await this.request(config, "/v1/control", {
      action, session_id: sessionId, revision
    });
    if (response.status !== 202) throw new Error("Breadcrumbs did not accept the timer command.");
    // A 202 queues work on the TUI thread. Do not pretend the timer changed
    // until a later status revision confirms that the command was applied.
    await this.refreshStatus();
  }

  async emptyPayload(sentAt = Date.now() / 1000) {
    return {
      ...await this.identities,
      browser: "chrome",
      focused: false,
      tab_id: null,
      window_id: null,
      title: "",
      title_key: "",
      url: "",
      domain: "",
      page_key: "",
      incognito: false,
      sent_at: sentAt,
      tabs: [],
      inventory_truncated: false
    };
  }

  async scheduleAlarm(enabled) {
    if (enabled) {
      await this.api.alarms.create(HEARTBEAT_ALARM, {periodInMinutes: 0.5});
      if (this.started && !this.interval) {
        // This timer is best effort; MV3 may suspend it.
        this.interval = setInterval(() => void this.sync(), 2000);
      }
    } else {
      await this.api.alarms.clear(HEARTBEAT_ALARM);
      clearInterval(this.interval);
      this.interval = null;
    }
  }

  scheduleSync() {
    this.eventRevision += 1;
    clearTimeout(this.eventTimer);
    this.eventTimer = setTimeout(() => {
      this.eventTimer = null;
      void this.sync();
    }, 60);
  }

  settleBrowser(generation, sequence, state) {
    if (generation !== this.generation || sequence < this.settledBrowserSequence) return;
    this.settledBrowserSequence = sequence;
    this.browserState = state;
  }

  acceptTabContext(payload, generation, sequence) {
    if (generation !== this.generation || sequence < this.settledBrowserSequence) return;
    this.tabContext = payload.focused && payload.domain ? {
      domain: payload.domain, title: payload.title || "", title_shared: this.serverStatus?.include_titles === true
    } : null;
    this.tabContextAt = performance.now();
  }

  async reportUnfocused() {
    this.tabContext = null;
    const generation = this.generation;
    const sequence = ++this.browserSequence;
    const sentAt = Date.now() / 1000;
    const config = await this.config();
    if (!config || !config.enabled || generation !== this.generation || !this.forceUnfocused) return;
    try {
      const payload = await this.emptyPayload(sentAt);
      if (generation === this.generation && this.forceUnfocused) {
        await this.request(config, "/v1/browser", payload);
        this.settleBrowser(generation, sequence, "connected");
      }
    } catch {
      this.settleBrowser(generation, sequence, "unavailable");
    }
  }

  bindEvents() {
    this.api.tabs.onActivated.addListener(() => this.scheduleSync());
    this.api.tabs.onUpdated.addListener(() => this.scheduleSync());
    this.api.tabs.onRemoved.addListener(() => this.scheduleSync());
    this.api.windows.onFocusChanged.addListener((windowId) => {
      this.forceUnfocused = windowId === this.api.windows.WINDOW_ID_NONE;
      this.eventRevision += 1;
      if (this.forceUnfocused) void this.reportUnfocused();
      this.scheduleSync();
    });
    this.api.alarms.onAlarm.addListener((alarm) => {
      if (alarm.name === HEARTBEAT_ALARM) void this.sync();
    });
    this.api.runtime.onMessage.addListener((message, _sender, respond) => {
      void this.handleMessage(message).then(respond);
      return true;
    });
    this.api.runtime.onStartup.addListener(() => void this.initialize());
    this.api.runtime.onInstalled.addListener(() => void this.initialize());
  }

  async initialize() {
    await this.identities;
    const config = await this.config();
    await this.scheduleAlarm(Boolean(config && config.enabled));
    await this.refreshStatus();
    // Timer pickup must not wait for tab enumeration, hashing, or a browser
    // report, including when this worker is waking into an already-running TUI.
    if (config && config.enabled) void this.sync();
  }

  start() {
    this.started = true;
    this.bindEvents();
    void this.initialize().catch(() => { this.connectionState = "unavailable"; });
  }

  async sync() {
    this.pending = true;
    if (this.syncing) return this.syncing;
    this.syncing = (async () => {
      do {
        this.pending = false;
        await this.syncOnce();
      } while (this.pending);
    })().finally(() => { this.syncing = null; });
    return this.syncing;
  }

  async syncOnce() {
    const browserSequence = ++this.browserSequence;
    const generation = this.generation;
    const revision = this.eventRevision;
    let statusReceived = false;
    let sequence = null;
    try {
      const config = await this.config();
      if (!config || !config.enabled) {
        this.browserState = config ? "paused" : "idle";
        return;
      }
      sequence = ++this.statusSequence;
      let status = await this.status(config);
      statusReceived = true;
      if (!this.acceptStatus(status, config, generation, sequence)) {
        if (generation !== this.generation || this.timerStale()) return;
        status = this.serverStatus;
      }
      if (generation !== this.generation || revision !== this.eventRevision) return;
      const payload = await this.emptyPayload();
      // Neither metadata API is queried until Breadcrumbs permits this operation.
      if (status.inventory_requested) {
        const tabs = await this.api.tabs.query({windowType: "normal"});
        const inventory = [];
        let bytes = 0;
        for (const tab of tabs) {
          if (generation !== this.generation || revision !== this.eventRevision) return;
          const item = await describeTab(tab, true);
          if (!item) continue;
          const itemBytes = new TextEncoder().encode(JSON.stringify(item)).length + 1;
          if (inventory.length >= 256 || bytes + itemBytes > 40000) {
            payload.inventory_truncated = true;
            break;
          }
          inventory.push(item);
          bytes += itemBytes;
        }
        payload.tabs = inventory;
      }
      if (status.active && !this.forceUnfocused) {
        if (generation !== this.generation || revision !== this.eventRevision) return;
        const window = await this.api.windows.getLastFocused({populate: false, windowTypes: ["normal"]});
        if (window && window.focused === true && !window.incognito && window.type === "normal") {
          const tabs = await this.api.tabs.query({active: true, windowId: window.id});
          const active = await describeTab(tabs[0], status.include_titles === true);
          if (active) Object.assign(payload, active, {focused: true});
        }
      }
      if (generation !== this.generation || revision !== this.eventRevision) return;
      if (this.forceUnfocused) {
        Object.assign(payload, {focused: false, tab_id: null, window_id: null, title: "", title_key: "", domain: "", page_key: ""});
      }
      await this.request(config, "/v1/browser", payload);
      if (generation !== this.generation) return;
      this.acceptTabContext(payload, generation, browserSequence);
      this.settleBrowser(generation, browserSequence, "connected");
    } catch {
      if (generation === this.generation) {
        this.settleBrowser(generation, browserSequence, "unavailable");
        if (!statusReceived && sequence !== null) this.rejectStatus(generation, sequence);
      }
    }
  }

  async state() {
    const config = await this.config();
    return {
      paired: Boolean(config),
      enabled: Boolean(config && config.enabled),
      endpoint: config ? config.endpoint : "",
      connection_state: config ? this.connectionState : "not_paired",
      browser_state: config ? this.browserState : "idle",
      active: Boolean(config && config.enabled && this.serverStatus && this.serverStatus.active),
      inventory_requested: Boolean(config && config.enabled && this.serverStatus && this.serverStatus.inventory_requested),
      last_contact: this.lastContact,
      timer: config ? normalizeTimer(this.serverStatus && this.serverStatus.timer) : null,
      timer_stale: Boolean(config && this.timerStale()),
      tab_context: config?.enabled && this.serverStatus?.active && !this.timerStale() && !this.forceUnfocused &&
        this.browserState !== "unavailable" && this.tabContextAt !== null &&
        performance.now() - this.tabContextAt <= 15000 && this.tabContext ? {...this.tabContext,
          title: this.serverStatus.include_titles === true ? this.tabContext.title : "",
          title_shared: this.serverStatus.include_titles === true} : null
    };
  }

  async pair(endpoint, token) {
    const generation = ++this.generation;
    const sequence = ++this.statusSequence;
    endpoint = normalizeEndpoint(endpoint);
    token = String(token || "").trim();
    if (token.length < 16 || token.length > 512 || /\s/.test(token)) {
      throw new Error("Paste the complete pairing token shown by Breadcrumbs.");
    }
    const status = await this.status({endpoint, token});
    if (generation !== this.generation) throw new Error("Connection changed while pairing.");
    await this.api.storage.local.set({endpoint, token, enabled: true});
    this.acceptStatus(status, {enabled: true}, generation, sequence);
    await this.scheduleAlarm(true);
    void this.sync();
  }

  async setEnabled(enabled) {
    const generation = ++this.generation;
    this.tabContext = null;
    const config = await this.config();
    if (!config) throw new Error("Pair this browser with Breadcrumbs first.");
    if (generation !== this.generation) return;
    await this.api.storage.local.set({enabled: enabled === true});
    await this.scheduleAlarm(enabled === true);
    if (enabled) {
      await this.refreshStatus();
      void this.sync();
    } else {
      if (this.connectionState !== "unavailable") this.connectionState = "paused";
      this.browserState = "paused";
      try {
        const payload = await this.emptyPayload();
        if (generation === this.generation) await this.request(config, "/v1/browser", payload);
      } catch {
        // Local pause takes effect even when the local server is unavailable.
      }
    }
  }

  async disconnect() {
    const generation = ++this.generation;
    const config = await this.config();
    await this.api.storage.local.remove(["endpoint", "token", "enabled"]);
    await this.scheduleAlarm(false);
    this.serverStatus = null;
    this.tabContext = null;
    this.connectionState = "not_paired";
    this.browserState = "idle";
    this.lastContact = null;
    this.lastStatusAt = null;
    if (config && generation === this.generation) {
      try {
        await this.request(config, "/v1/browser", await this.emptyPayload());
      } catch {
        // The token is already removed locally; no automatic reconnect occurs.
      }
    }
  }

  async handleMessage(message) {
    try {
      if (!message || typeof message.type !== "string") return {ok: false, error: "Unknown request."};
      if (message.type === "pair") await this.pair(message.endpoint, message.token);
      else if (message.type === "start") await this.setEnabled(true);
      else if (message.type === "stop") await this.setEnabled(false);
      else if (message.type === "disconnect") await this.disconnect();
      else if (message.type === "timer-control") {
        await this.control(message.action, message.session_id, message.revision);
        return {ok: true, accepted: true, state: await this.state()};
      }
      else if (message.type === "get-state") {
        await this.refreshStatus();
        // A block may have started in the TUI while the same Chrome tab stayed
        // foreground. Prompt collection without making timer pickup wait for it.
        const config = await this.config();
        if (config && config.enabled && !this.timerStale() && this.serverStatus &&
            (this.serverStatus.active || this.serverStatus.inventory_requested) && !this.syncing) {
          void this.sync();
        }
      }
      else return {ok: false, error: "Unknown request."};
      return {ok: true, state: await this.state()};
    } catch (error) {
      if (message && message.type === "timer-control") await this.refreshStatus();
      // Only our own fixed messages are returned; payloads/URLs/tokens are not logged.
      const known = [PUBLIC_ERROR, "Connection changed while pairing.", "Pair this browser with Breadcrumbs first.",
        "Paste the complete pairing token shown by Breadcrumbs.",
        "Use the connection URL shown by Breadcrumbs: http://127.0.0.1:PORT",
        "Only http://127.0.0.1:PORT connection URLs are accepted.",
        CONTROL_CONFLICT, CONTROL_UNAVAILABLE, "Invalid timer command.",
        "Breadcrumbs did not accept the timer command."];
      return {ok: false, error: known.includes(error.message) ? error.message : PUBLIC_ERROR, state: await this.state()};
    }
  }
}

if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.id) {
  new BrowserBridge(chrome).start();
}
