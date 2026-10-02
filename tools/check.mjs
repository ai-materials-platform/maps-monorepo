import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fail = (msg) => { console.error('CHECK FAIL: ' + msg); process.exit(1); };
const ok = (msg) => console.log('ok - ' + msg);

// 1. layout
for (const dir of ['apps/prediction', 'apps/simulation', 'apps/shell', 'projects', 'tools']) {
  if (!fs.existsSync(path.join(root, dir))) fail('missing dir: ' + dir);
}
ok('monorepo layout');

// 2. key files
const required = [
  'package.json',
  'requirements.txt',
  '.env.example',
  'apps/prediction/main.py',
  'apps/prediction/requirements.txt',
  'apps/prediction/models/pretrained_material_model.pkl',
  'apps/simulation/backend/simulation_server.py',
  'apps/simulation/package.json',
  'apps/simulation/vite.config.js',
  'apps/shell/electron/main.cjs',
  'apps/shell/electron/preload.cjs',
  'apps/shell/renderer/index.html',
  'apps/shell/renderer/app.js',
  'apps/shell/renderer/prediction.js',
  'apps/shell/package.json',
];
for (const f of required) {
  if (!fs.existsSync(path.join(root, f))) fail('missing file: ' + f);
}
ok('key files present');

// 3. no nested git
for (const d of ['apps/prediction/.git', 'apps/simulation/.git', 'apps/shell/.git']) {
  if (fs.existsSync(path.join(root, d))) fail('nested git remains: ' + d);
}
ok('no nested .git');

// 4. no duplicate node apps (prediction must be python-only)
for (const f of ['apps/prediction/package.json', 'apps/prediction/electron/main.cjs']) {
  if (fs.existsSync(path.join(root, f))) fail('duplicate remains: ' + f);
}
ok('no duplicate electron in prediction');

// 5. shell points at monorepo siblings
const shellMain = fs.readFileSync(path.join(root, 'apps/shell/electron/main.cjs'), 'utf8');
if (!shellMain.includes("'..', 'prediction'") || !shellMain.includes("'..', 'simulation'")) {
  fail('shell main.cjs still points at old external paths');
}
if (shellMain.includes("ai-materials-discovery-platform-simulation") && !shellMain.includes("isPackaged")) {
  fail('shell main.cjs dev default not updated');
}
ok('shell paths point to apps/*');

// 6. simulation backend finds monorepo prediction
const simServer = fs.readFileSync(path.join(root, 'apps/simulation/backend/simulation_server.py'), 'utf8');
if (!simServer.includes('"prediction"') && !simServer.includes("'prediction'")) {
  fail('simulation_server.py does not reference apps/prediction');
}
ok('simulation backend monorepo-aware');

// 7. JS syntax check
for (const f of ['apps/shell/electron/main.cjs', 'apps/shell/electron/preload.cjs', 'apps/shell/renderer/app.js']) {
  try {
    new vm.Script(fs.readFileSync(path.join(root, f), 'utf8'), { filename: f });
  } catch (e) {
    fail('syntax error in ' + f + ': ' + e.message);
  }
}
ok('electron/renderer syntax');

// 8. python syntax check (stdlib compile)
try {
  execSync('python -m py_compile apps/prediction/main.py apps/simulation/backend/simulation_server.py apps/prediction/src/api/server.py', { cwd: root, stdio: 'pipe' });
} catch (e) {
  fail('python py_compile failed');
}
ok('python compiles');

console.log('\nAll monorepo checks passed.');
