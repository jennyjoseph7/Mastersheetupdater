const fs = require('fs');
const path = require('path');

const out = path.join(__dirname, '..', 'out');
if (!fs.existsSync(out)) { console.log('out/ not found, skipping'); process.exit(0); }

const items = fs.readdirSync(out, { withFileTypes: true });
for (const item of items) {
  if (!item.isDirectory()) continue;
  const pageDir = path.join(out, item.name);
  const sub = fs.readdirSync(pageDir, { withFileTypes: true });
  for (const entry of sub) {
    if (!entry.isDirectory() || !entry.name.startsWith('__next.')) continue;
    const nestedFile = path.join(pageDir, entry.name, '__PAGE__.txt');
    if (!fs.existsSync(nestedFile)) continue;
    const flatFile = path.join(pageDir, entry.name.replace('/', '.') + '.__PAGE__.txt');
    if (!fs.existsSync(flatFile)) {
      fs.cpSync(nestedFile, flatFile);
      console.log('  + ' + path.relative(out, flatFile));
    }
  }
}
console.log('postbuild: RSC compat copies done');
