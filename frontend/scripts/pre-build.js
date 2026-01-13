#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const appDir = path.join(__dirname, '../app');
const tempDir = path.join(__dirname, '../.api-temp');

// Create temp directory if it doesn't exist
if (!fs.existsSync(tempDir)) {
  fs.mkdirSync(tempDir, { recursive: true });
}

// Move API directories to temp
const apiDirs = ['api', 'api.backup'];

apiDirs.forEach(dir => {
  const sourcePath = path.join(appDir, dir);
  const destPath = path.join(tempDir, dir);
  
  if (fs.existsSync(sourcePath)) {
    console.log(`Moving ${dir} to temp directory...`);
    // Remove destination if it exists
    if (fs.existsSync(destPath)) {
      fs.rmSync(destPath, { recursive: true, force: true });
    }
    // Move source to destination
    fs.renameSync(sourcePath, destPath);
    console.log(`✓ Moved ${dir}`);
  }
});

console.log('✓ Pre-build script completed: API routes moved to temp directory');
