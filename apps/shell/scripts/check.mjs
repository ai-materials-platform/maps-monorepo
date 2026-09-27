import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const root = path.resolve(process.cwd());
const required = [
  'package.json',
  'electron/main.cjs',
  'electron/preload.cjs',
  'renderer/index.html',
  'renderer/styles.css',
  'renderer/app.js'
];

for (const file of required) {
  const target = path.join(root, file);
  if (!fs.existsSync(target)) throw new Error(`Missing required file: ${file}`);
}

for (const file of ['electron/main.cjs', 'electron/preload.cjs', 'renderer/app.js']) {
  const code = fs.readFileSync(path.join(root, file), 'utf8');
  new vm.Script(code, { filename: file });
}

const packageJson = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
if (!packageJson.scripts?.dev || !packageJson.scripts?.check) throw new Error('package scripts are incomplete');

console.log('Integrated platform scaffold check passed.');
