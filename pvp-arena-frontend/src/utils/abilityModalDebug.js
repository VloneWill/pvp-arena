/**
 * Debug logger for ability modal (tooltip popup) on iOS.
 * Zero impact when debug is off. Persists to localStorage and in-memory; overlay shows last 20.
 */

const STORAGE_KEY = "abilityModalLogs";
const MAX_STORED = 200;
const MAX_IN_MEMORY = 200;

let inMemoryLogs = [];
let listeners = new Set();

function getStored() {
  if (typeof localStorage === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.slice(-MAX_STORED) : [];
  } catch {
    return [];
  }
}

function persist(logs) {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(logs.slice(-MAX_STORED)));
  } catch (_) {}
}

/**
 * Debug mode is on if localStorage.debugAbilityModal === "1" or URL has ?debugAbilityModal=1
 */
export function isDebugEnabled() {
  if (typeof window === "undefined") return false;
  if (localStorage.getItem("debugAbilityModal") === "1") return true;
  const params = new URLSearchParams(window.location.search);
  return params.get("debugAbilityModal") === "1";
}

/**
 * Log an event. Only persists and notifies when debug is enabled.
 * @param {string} eventName - e.g. TRIGGER_TAP, MODAL_OPEN, MODAL_CLOSE, POLL_TICK, OUTSIDE_HANDLER_FIRED, MODAL_MOUNT, MODAL_UNMOUNT, RESIZE, VISUAL_VIEWPORT_RESIZE, CLEAR_DUE_TO_POLL
 * @param {object} [fields] - optional payload (turn, matchId, abilityId, modalOpen, reason, eventType, targetTag, etc.)
 */
export function log(eventName, fields = {}) {
  if (!isDebugEnabled()) return;
  const now = Date.now();
  const entry = {
    ts: now,
    iso: new Date(now).toISOString(),
    event: eventName,
    ...fields,
  };
  inMemoryLogs.push(entry);
  if (inMemoryLogs.length > MAX_IN_MEMORY) inMemoryLogs = inMemoryLogs.slice(-MAX_IN_MEMORY);
  persist(inMemoryLogs);
  listeners.forEach((cb) => {
    try { cb(entry); } catch (_) {}
  });
}

/**
 * Get all stored logs (from memory, capped).
 */
export function getLogs() {
  if (inMemoryLogs.length > 0) return inMemoryLogs;
  inMemoryLogs = getStored();
  return inMemoryLogs;
}

/**
 * Subscribe to new log entries (for overlay refresh). Returns unsubscribe.
 */
export function subscribe(callback) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

/**
 * Clear logs from memory and localStorage.
 */
export function clearLogs() {
  inMemoryLogs = [];
  persist(inMemoryLogs);
  listeners.forEach((cb) => {
    try { cb(null); } catch (_) {}
  });
}
