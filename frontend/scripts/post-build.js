#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const appDir = path.join(__dirname, '../app');
const tempDir = path.join(__dirname, '../.api-temp');

// Move API directories back from temp
const apiDirs = ['api', 'api.backup'];

apiDirs.forEach(dir => {
  const sourcePath = path.join(tempDir, dir);
  const destPath = path.join(appDir, dir);
  
  if (fs.existsSync(sourcePath)) {
    console.log(`Moving ${dir} back from temp directory...`);
    // Remove destination if it exists
    if (fs.existsSync(destPath)) {
      fs.rmSync(destPath, { recursive: true, force: true });
    }
    // Move source back to destination
    fs.renameSync(sourcePath, destPath);
    console.log(`✓ Moved ${dir} back`);
  }
});

// Clean up temp directory
if (fs.existsSync(tempDir)) {
  try {
    fs.rmSync(tempDir, { recursive: true, force: true });
    console.log('✓ Cleaned up temp directory');
  } catch (err) {
    // Ignore errors during cleanup
  }
}

console.log('✓ Post-build script completed: API routes restored');
