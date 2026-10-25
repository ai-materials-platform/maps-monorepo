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
