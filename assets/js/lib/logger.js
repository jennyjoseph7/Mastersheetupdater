/**
 * logger.js — Shared structured console logger
 *
 * Adds tagged, timestamped console messages consistent across all pages.
 * Mimics the pattern: [Tag] Message
 *
 * Functions:
 *   $log(tag, msg, data?)   — console.log with [Tag] prefix
 *   $warn(tag, msg, data?)  — console.warn
 *   $error(tag, msg, data?) — console.error
 *   $start(tag, msg)        — console.group + log start
 *   $end()                  — console.groupEnd
 *
 * Tags used across the app:
 *   App   — page load, lifecycle
 *   Auth  — login, token check, redirect
 *   Theme — dark/light toggle
 *   Nav   — navigation load, active state
 *   API   — fetch calls, responses
 *   AI    — LLM calls, validation
 *   Conf  — config, feature flags
 */
(function () {
  'use strict';

  var PAD_WIDTH = 5; // fixed width so tags align in console

  function padTag(tag) {
    // Right-pad to PAD_WIDTH for alignment
    while (tag.length < PAD_WIDTH) tag += ' ';
    if (tag.length > PAD_WIDTH) tag = tag.slice(0, PAD_WIDTH);
    return tag;
  }

  window.$log = function (tag, msg, data) {
    var prefix = '[' + padTag(tag) + ']';
    if (data !== undefined) {
      console.log(prefix, msg, data);
    } else {
      console.log(prefix, msg);
    }
  };

  window.$warn = function (tag, msg, data) {
    var prefix = '[' + padTag(tag) + ']';
    if (data !== undefined) {
      console.warn(prefix, msg, data);
    } else {
      console.warn(prefix, msg);
    }
  };

  window.$error = function (tag, msg, data) {
    var prefix = '[' + padTag(tag) + ']';
    if (data !== undefined) {
      console.error(prefix, msg, data);
    } else {
      console.error(prefix, msg);
    }
  };

  window.$start = function (tag, msg) {
    var prefix = '[' + padTag(tag) + ']';
    console.group(prefix, msg);
  };

  window.$end = function () {
    console.groupEnd();
  };

  /**
   * $mask(val, type) — PII-safe masking for log output
   *
   * type 'phone': shows only last 4 digits  (e.g. "******3210")
   * type 'email': shows first char + *** + domain (e.g. "j***@example.com")
   * type 'user':  alias for 'email'
   * default:      returns the value as-is
   */
  window.$mask = function (val, type) {
    if (!val) return '(empty)';
    var s = String(val);
    if (!s) return '(empty)';
    if (type === 'phone') {
      // Show only last 4 digits
      var digits = s.replace(/\D/g, '');
      if (digits.length <= 4) return digits;
      return '******' + digits.slice(-4);
    }
    if (type === 'email' || type === 'user') {
      var atIdx = s.indexOf('@');
      if (atIdx > 0) {
        // Email: first char + *** + domain
        return s.charAt(0) + '***' + s.slice(atIdx);
      }
      // Generic user ID without @: show first + last char
      if (s.length <= 2) return s.charAt(0) + '*';
      return s.charAt(0) + '***' + s.charAt(s.length - 1);
    }
    return s;
  };
})();
