#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const appDir = path.join(__dirname, "src", "app");
const forbiddenExtensions = new Set([".scss"]);

function collectForbiddenFiles(currentDir, results) {
  let entries;

  try {
    entries = fs.readdirSync(currentDir, { withFileTypes: true });
  } catch (error) {
    console.error(`[style-check] Could not read directory: ${currentDir}`);
    console.error(`[style-check] ${error.message}`);
    process.exit(1);
  }

  for (const entry of entries) {
    const fullPath = path.join(currentDir, entry.name);

    if (entry.isDirectory()) {
      collectForbiddenFiles(fullPath, results);
      continue;
    }

    if (!entry.isFile()) {
      continue;
    }

    const extension = path.extname(entry.name).toLowerCase();
    if (forbiddenExtensions.has(extension)) {
      results.push(path.relative(__dirname, fullPath));
    }
  }
}

if (!fs.existsSync(appDir)) {
  console.error(`[style-check] Directory not found: ${appDir}`);
  process.exit(1);
}

const forbiddenFiles = [];
collectForbiddenFiles(appDir, forbiddenFiles);

if (forbiddenFiles.length > 0) {
  console.error("[style-check] Forbidden style files detected in src/app:");
  for (const file of forbiddenFiles) {
    console.error(` - ${file}`);
  }
  console.error(
    "[style-check] Use Tailwind utility classes in templates and remove .scss files."
  );
  process.exit(1);
}

console.log("[style-check] OK: no .scss files found in src/app.");
