export function normalizeEndpoint(value) {
  let url;
  try {
    url = new URL(String(value).trim());
  } catch {
    throw new Error("Use the connection URL shown by Breadcrumbs: http://127.0.0.1:PORT");
  }
  if (url.protocol !== "http:" || url.hostname !== "127.0.0.1" ||
      !url.port || url.username || url.password ||
      (url.pathname !== "/" && url.pathname !== "") || url.search || url.hash) {
    throw new Error("Only http://127.0.0.1:PORT connection URLs are accepted.");
  }
  return url.origin;
}

export async function digest(value) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(bytes), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function normalizeTimer(value) {
  if (!value || typeof value !== "object" ||
      !["ready", "running", "paused", "finished"].includes(value.status) ||
      !(value.session_id === null || (Number.isSafeInteger(value.session_id) && value.session_id > 0)) ||
      !Number.isSafeInteger(value.revision) || value.revision < 0 ||
      !Number.isFinite(value.remaining_seconds) || value.remaining_seconds < 0 ||
      (["running", "paused"].includes(value.status) && value.session_id === null)) {
    return null;
  }
  return {
    status: value.status,
    session_id: value.session_id,
    name: typeof value.name === "string" ? value.name.replace(/[\u0000-\u001f\u007f-\u009f]/g, " ").slice(0, 120) : "",
    remaining_seconds: value.remaining_seconds,
    kind: ["focus", "short_break", "long_break", "custom"].includes(value.kind) ? value.kind : "focus",
    can_control: value.can_control === true,
    ui_theme: ["midnight", "gameboy", "sunset"].includes(value.ui_theme) ? value.ui_theme : "midnight",
    revision: value.revision
  };
}

export function timerPrimaryAction(timer) {
  return timer ? ({ready: "start", running: "pause", paused: "resume"})[timer.status] || null : null;
}

export function formatRemaining(value) {
  const seconds = Math.max(0, Math.ceil(Number.isFinite(value) ? value : 0));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;
  return (hours ? String(hours).padStart(2, "0") + ":" : "") +
    String(minutes).padStart(2, "0") + ":" + String(remainder).padStart(2, "0");
}

export async function describeTab(tab, includeTitle = false) {
  if (!tab || tab.incognito || !Number.isInteger(tab.id) || !Number.isInteger(tab.windowId)) {
    return null;
  }
  let url;
  try {
    url = new URL(tab.url);
  } catch {
    return null;
  }
  if (!["http:", "https:"].includes(url.protocol) || !url.hostname) {
    return null;
  }
  // Queries can identify a page (for example YouTube's watch?v=VIDEO_ID).
  // Keep them only in the local hash input, never in the emitted payload.
  url.username = "";
  url.password = "";
  url.hash = "";
  const title = typeof tab.title === "string" ? tab.title : "";
  return {
    tab_id: tab.id,
    window_id: tab.windowId,
    title: includeTitle ? title.slice(0, 160) : "",
    domain: url.hostname.toLowerCase().replace(/\.$/, ""),
    page_key: await digest(url.href),
    title_key: title.trim() ? await digest(title.trim().toLowerCase()) : ""
  };
}
