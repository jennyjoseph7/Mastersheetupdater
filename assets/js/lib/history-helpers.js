/**
 * history-helpers.js — Shared session history detection & formatting
 *
 * Extracted from disposition_sync_v2.html and post_sales_disposition.html
 * to avoid duplication. Provides:
 *   detectHistory(obj)        – Find history column in a session row
 *   parseHistoryJson(raw)     – Safely parse history JSON into an array
 *   formatRelativeOffset(firstTs, currentTs) – Format a timestamp offset as [m:ss] or [h:mm:ss].
 *       @param {number} firstTs   - Epoch ms of the first message in the conversation.
 *       @param {number} currentTs - Epoch ms of the current message.
 *       @returns {string} Formatted offset like "[0:05]" or "[1:02:30]".
 *   normalizeRoleLabel(role)  – Normalise agent/assistant/bot → Agent, etc.
 *   formatHistoryForPrompt(r) – Convert raw history into readable transcript text
 */

/**
 * @param {number} firstTs   - Epoch ms of the first message in the conversation.
 * @param {number} currentTs - Epoch ms of the current message.
 * @returns {string} Formatted offset like "[0:05]" for durations <1h or "[1:02:30]" for ≥1h.
 */

// ─── DETECTION ────────────────────────────────────────────────────────────
window.detectHistory = function detectHistory(obj) {
  if (!obj) { $log('Data', 'detectHistory — object is null/undefined'); return ''; }
  var candidates = ['history', 'session_history', 'transcript', 'conversation_history', 'chat_history', 'messages'];
  for (var i = 0; i < candidates.length; i++) {
    var c = candidates[i];
    if (obj[c] !== undefined && obj[c] !== '') {
      var val = String(obj[c]).trim();
      $log('Data', 'detectHistory — found in column "' + c + '" (' + val.length + ' chars)');
      return val;
    }
  }
  // Fallback: check raw values for JSON-like content with role+message
  if (Array.isArray(obj.__raw)) {
    for (var j = 0; j < obj.__raw.length; j++) {
      var v = String(obj.__raw[j] || '').trim();
      if (v.length > 10 && (v.includes('"role"') || v.includes("'role'")) && (v.includes('"message"') || v.includes("'message'"))) {
        $log('Data', 'detectHistory — found in __raw[' + j + '] via fallback (' + v.length + ' chars)');
        return v;
      }
    }
  }
  $log('Data', 'detectHistory — no history found');
  return '';
};

// ─── JSON PARSING ─────────────────────────────────────────────────────────
window.parseHistoryJson = function parseHistoryJson(raw) {
  if (!raw) return null;
  if (typeof raw === 'string') {
    try {
      var parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
      return null;
    } catch(e) {
      return null;
    }
  }
  if (Array.isArray(raw)) return raw;
  return null;
};

// ─── TIMESTAMP OFFSET ─────────────────────────────────────────────────────
window.formatRelativeOffset = function formatRelativeOffset(firstTs, currentTs) {
  if (!firstTs || !currentTs) return '';
  var diff = Math.floor((currentTs - firstTs) / 1000);
  if (diff < 0) diff = 0;
  var mins = Math.floor(diff / 60);
  var secs = diff % 60;
  if (mins >= 60) {
    var hrs = Math.floor(mins / 60);
    mins = mins % 60;
    return '[' + hrs + ':' + String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0') + ']';
  }
  return '[' + mins + ':' + String(secs).padStart(2, '0') + ']';
};

// ─── ROLE LABEL NORMALISATION ─────────────────────────────────────────────
window.normalizeRoleLabel = function normalizeRoleLabel(role) {
  var r = String(role || '').toLowerCase().trim();
  if (r === 'agent' || r === 'assistant' || r === 'bot') return 'Agent';
  if (r === 'user' || r === 'customer') return 'Customer';
  return 'Unknown';
};

// ─── FORMAT HISTORY FOR PROMPT ────────────────────────────────────────────
window.formatHistoryForPrompt = function formatHistoryForPrompt(raw) {
  var entries = window.parseHistoryJson(raw);
  if (!entries || !entries.length) {
    $log('Data', 'formatHistoryForPrompt — no entries to format');
    return '';
  }

  $log('Data', 'formatHistoryForPrompt — formatting ' + entries.length + ' history entries');

  var lines = [];
  var firstTs = null;

  // Find first valid timestamp
  for (var i = 0; i < entries.length; i++) {
    var e = entries[i];
    if (e && e.timestamp) {
      var ts = typeof e.timestamp === 'number' ? e.timestamp * 1000 : Number(e.timestamp);
      if (Number.isFinite(ts) && ts > 1000000000000) {
        firstTs = ts;
        $log('Data', 'formatHistoryForPrompt — first timestamp at entry ' + i);
        break;
      }
    }
  }

  var messageCount = 0;
  for (var j = 0; j < entries.length; j++) {
    var entry = entries[j];
    if (!entry) continue;
    var msg = String(entry.message || '').trim();
    if (!msg) continue;
    messageCount++;
    var label = window.normalizeRoleLabel(entry.role);
    var timePrefix = '';
    if (firstTs && entry.timestamp) {
      var currentTs = typeof entry.timestamp === 'number' ? entry.timestamp * 1000 : Number(entry.timestamp);
      if (Number.isFinite(currentTs)) {
        timePrefix = window.formatRelativeOffset(firstTs, currentTs) + ' ';
      }
    }
    // Collapse whitespace
    msg = msg.replace(/\s+/g, ' ');
    lines.push(timePrefix + label + ': ' + msg);
  }

  $log('Data', 'formatHistoryForPrompt — ' + messageCount + ' messages formatted into ' + lines.length + ' lines (' + (lines.join('\n').length) + ' chars)');
  return lines.join('\n');
};
