/* init.js — Theme + auth gate (runs before page renders to prevent flash) */
(function() {
  var theme = localStorage.getItem('jejo-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', theme);

  function requireAuth() {
    var token = sessionStorage.getItem('gryd_token');
    var expiry = sessionStorage.getItem('gryd_expiry');

    // Fallback/sync from localStorage
    if (!token && localStorage.getItem('gryd_token')) {
      var localToken = localStorage.getItem('gryd_token');
      var localExpiry = localStorage.getItem('gryd_expiry');
      var localExpiryVal = parseInt(localExpiry);
      var localNow = Math.floor(Date.now() / 1000);
      if (localToken && !isNaN(localExpiryVal) && localExpiryVal > localNow) {
        token = localToken;
        expiry = localExpiry;
        sessionStorage.setItem('gryd_token', token);
        sessionStorage.setItem('gryd_expiry', expiry);
        sessionStorage.setItem('gryd_session_id', localStorage.getItem('gryd_session_id') || '');
        sessionStorage.setItem('gryd_enterprise_id', localStorage.getItem('gryd_enterprise_id') || 'autocrm');
        sessionStorage.setItem('gryd_user_id', localStorage.getItem('gryd_user_id') || '');
      }
    }

    if (!token || !expiry || parseInt(expiry) <= Math.floor(Date.now() / 1000)) {
      window.location.replace('../login.html');
      return false;
    }
    return true;
  }

  requireAuth();

  // Re-check on bfcache restore (back/forward navigation).
  // Check on EVERY pageshow, not just persisted — some browsers don't set persisted correctly.
  window.addEventListener('pageshow', function() { requireAuth(); });

  // Also check on visibility change — covers cases where bfcache fires
  // but pageshow fires before sessionStorage is updated.
  document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') requireAuth();
  });

  // Prevent bfcache by registering unload listener.
  // This forces a fresh page load on back/forward, so auth gate always runs.
  window.addEventListener('unload', function() {});
})();
