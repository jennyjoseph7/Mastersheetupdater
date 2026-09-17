const XLSX = require('xlsx');

function clean(val) {
  if (val == null) return '';
  return String(val).replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function canonicalHeader(raw) {
  return clean(raw).toLowerCase().replace(/[^a-z0-9_]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
}

function cellToString(val) {
    if (val == null) return '';
    if (typeof val === 'number') {
      if (Number.isInteger(val)) return String(val);
      if (val > 999999 && Math.abs(val - Math.round(val)) < 0.01) return String(Math.round(val));
      return String(val);
    }
    let s = String(val).trim();
    if (/^\d[\d.]*[eE][+\-]?\d+$/.test(s)) {
      const n = parseFloat(s);
      if (isFinite(n) && n > 999999) return String(Math.round(n));
    }
    return s;
}

// Just checking logic, we don't have the user's actual excel file...
// Wait, I can't read the user's Excel file because it's uploaded via browser!
// I need to add console.log in the browser code so the user can check the console.
