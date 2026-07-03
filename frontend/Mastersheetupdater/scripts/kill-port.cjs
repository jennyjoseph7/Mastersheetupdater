const { execSync } = require('child_process');
try {
  const out = execSync('netstat -ano', { encoding: 'utf8', timeout: 15000 });
  for (const line of out.split('\n')) {
    if (line.includes(':3000') && line.includes('LISTENING')) {
      const pid = line.trim().split(/\s+/).pop();
      if (pid && !isNaN(Number(pid))) execSync(`tskill ${pid}`, { stdio: 'ignore' });
    }
  }
} catch {}
