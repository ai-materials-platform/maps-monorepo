// 실행: node --test apps/shared/theme-sync.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';

const { readTheme, writeTheme, watchTheme } = createRequire(import.meta.url)('./theme-sync.cjs');
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'maps-theme-'));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

test('missing file reads as light', () => {
  assert.equal(readTheme(path.join(dir, 'none', 'theme.json')), 'light');
});

test('broken or invalid file reads as light and is rewritten', () => {
  const f = path.join(dir, 'broken.json');
  fs.writeFileSync(f, '{not json');
  assert.equal(readTheme(f), 'light');
  assert.deepEqual(JSON.parse(fs.readFileSync(f, 'utf8')), { theme: 'light' });
  fs.writeFileSync(f, '{"theme":"purple"}');
  assert.equal(readTheme(f), 'light');
});

test('write then read round-trips', () => {
  const f = path.join(dir, 'sub', 'theme.json');
  writeTheme('dark', f);
  assert.equal(readTheme(f), 'dark');
});

test('watch fires once per real change only', async () => {
  const f = path.join(dir, 'watch', 'theme.json');
  writeTheme('light', f);
  const seen = [];
  const stop = watchTheme((t) => seen.push(t), f);
  await sleep(150);
  writeTheme('dark', f);
  writeTheme('dark', f); // 같은 값 다시 쓰기 — 알림 없어야 함
  await sleep(500);
  writeTheme('light', f);
  await sleep(500);
  stop();
  assert.deepEqual(seen, ['dark', 'light']);
});

test('writeTheme ignores values other than light/dark', () => {
  const f = path.join(dir, 'invalid.json');
  writeTheme('dark', f);
  writeTheme('purple', f);
  writeTheme(undefined, f);
  assert.equal(readTheme(f), 'dark');
});

test('reading while another process writes never resets the theme to light', async () => {
  // 다른 앱(별도 프로세스)이 'dark'만 계속 쓰는 동안 읽는다 — 반쪽 파일을 '깨짐'으로 보고 라이트로 덮어쓰면 안 된다
  const f = path.join(dir, 'race.json');
  const done = f + '.done';
  writeTheme('dark', f);
  const { spawn } = await import('node:child_process');
  const lib = JSON.stringify(path.join(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/, '$1')), 'theme-sync.cjs'));
  const child = spawn(process.execPath, ['-e',
    `const {writeTheme}=require(${lib});for(let i=0;i<1500;i++)writeTheme('dark',${JSON.stringify(f)});require('fs').writeFileSync(${JSON.stringify(done)},'1')`]);
  let stderr = '';
  child.stderr.on('data', (d) => { stderr += d; });
  const seen = { light: 0, dark: 0 };
  while (!fs.existsSync(done) && child.exitCode === null) {
    seen[readTheme(f)] += 1;
    await sleep(0);
  }
  await new Promise((r) => (child.exitCode !== null ? r() : child.on('exit', r)));
  assert.equal(stderr, '', 'writer process failed');
  assert.ok(seen.dark > 10, JSON.stringify(seen));
  assert.equal(seen.light, 0, JSON.stringify(seen));
});
