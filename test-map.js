const leadMap = new Map();

const phones = ["9999999999", "919999999999"];
let lead = { id: 1 };

for (const p of phones) {
  leadMap.set(p, lead);
  leadMap.set('91' + p, lead);
  if (p.length === 10) leadMap.set(p, lead);
  if (p.startsWith('91') && p.length === 12) leadMap.set(p.slice(2), lead);
}

console.log(leadMap.keys());

const sPhones = ["9999999999"];
let matchedLead = null;
for (const sp of sPhones) {
  if (leadMap.has(sp)) { matchedLead = leadMap.get(sp); break; }
  if (sp.length === 10 && leadMap.has('91' + sp)) { matchedLead = leadMap.get('91' + sp); break; }
  if (sp.startsWith('91') && sp.length === 12 && leadMap.has(sp.slice(2))) { matchedLead = leadMap.get(sp.slice(2)); break; }
}

console.log(matchedLead);
