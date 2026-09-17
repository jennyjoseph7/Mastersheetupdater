function normalizePhone(raw) {
  if (raw == null) return null;
  let s = String(raw).trim();
  if (!s) return null;

  if (/^\d[\d.]*[eE][+\-]?\d+$/.test(s)) {
    const parsed = parseFloat(s);
    if (!isNaN(parsed)) {
      s = String(Math.round(parsed));
    }
  }

  const digits = s.replace(/\D/g, '');
  if (!digits) return null;

  if (digits.startsWith('91') && digits.length === 12) return digits.slice(2);
  if (digits.startsWith('0') && digits.length === 11) return digits.slice(1);
  if (digits.length === 10) return digits;
  if (digits.startsWith('91') && digits.length > 12) return digits.slice(digits.length - 10);
  if (digits.length > 10) return digits.slice(-10);

  return digits.length >= 7 ? digits : null;
}

console.log(normalizePhone("9.19881E+11"));
console.log(normalizePhone("+919999999999"));
console.log(normalizePhone("9999999999"));
