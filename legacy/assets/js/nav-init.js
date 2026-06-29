/* nav-init.js — Loads nav.html safely after ai-config.js defines loadNavSafe */
$log('Nav', 'Initializing navigation...');
if (typeof loadNavSafe === 'function') {
  $log('Nav', 'loadNavSafe ready — loading now');
  loadNavSafe('navContainer');
} else {
  $log('Nav', 'loadNavSafe not ready — deferring to DOMContentLoaded');
  document.addEventListener('DOMContentLoaded', function() {
    if (typeof loadNavSafe === 'function') loadNavSafe('navContainer');
  });
}
