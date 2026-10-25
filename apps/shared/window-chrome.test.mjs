// 실행: node --test apps/shared/window-chrome.test.mjs  (Electron 없이 도는 순수 부분만)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import chrome from './window-chrome.cjs';
import { menusFor } from './menu-model.js';

const spec = JSON.parse(fs.readFileSync(new URL('./menus.json', import.meta.url), 'utf8'));
const find = (tpl, label) => tpl.flatMap((m) => m.submenu).find((i) => i.label === label);

test('role ids become electron roles with their accelerator', () => {
  const tpl = chrome.menuTemplate(menusFor(spec, 'shell'), () => {});
  const copy = find(tpl, '복사');
  assert.equal(copy.role, 'copy');
  assert.equal(copy.accelerator, 'Ctrl+C');
  assert.equal(copy.click, undefined);
});

test('app ids click through to onClick with their id', () => {
  const seen = [];
  const tpl = chrome.menuTemplate(menusFor(spec, 'shell'), (id) => seen.push(id));
  const dash = find(tpl, '대시보드');
  assert.equal(dash.role, undefined);
  dash.click();
  assert.deepEqual(seen, ['view.nav.dashboard']);
});

test('separators and disabled items carry over', () => {
  const tpl = chrome.menuTemplate(menusFor(spec, 'sim', { handled: (id) => id !== 'file.report' }), () => {});
  assert.ok(tpl.find((m) => m.label === '편집').submenu.some((i) => i.type === 'separator'));
  assert.equal(tpl[0].submenu[0].enabled, false);
});

test('chromeOptions reads overlay colors from maps-theme.css', () => {
  assert.deepEqual(chrome.chromeOptions('light'),
    { titleBarStyle: 'hidden', titleBarOverlay: { color: '#FFFFFF', symbolColor: '#111827', height: 30 } });
  assert.equal(chrome.chromeOptions('dark').titleBarOverlay.color, '#1E1E1E');
});
