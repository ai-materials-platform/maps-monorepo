// 실행: node --test apps/shared/menu-model.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { menusFor, nextIndex } from './menu-model.js';

const spec = JSON.parse(fs.readFileSync(new URL('./menus.json', import.meta.url), 'utf8'));
const flat = (menus) => menus.flatMap((m) => m.items);
const find = (menus, id) => flat(menus).find((i) => i.id === id);

test('every app gets the same four menus', () => {
  for (const app of ['shell', 'pyqt', 'sim']) {
    assert.deepEqual(menusFor(spec, app).map((m) => m.id), ['file', 'edit', 'view', 'help'], app);
  }
});

test('items of other apps and devOnly items are dropped', () => {
  const shell = menusFor(spec, 'shell');
  assert.equal(find(shell, 'file.report'), undefined);        // sim 전용
  assert.equal(find(shell, 'view.devtools'), undefined);      // devOnly, dev=false
  assert.ok(find(menusFor(spec, 'shell', { dev: true }), 'view.devtools'));
});

test('no leading, trailing or double separators', () => {
  for (const app of ['shell', 'pyqt', 'sim']) {
    for (const m of menusFor(spec, app)) {
      const seps = m.items.map((i) => !!i.separator);
      assert.ok(!seps[0] && !seps.at(-1), `${app}/${m.id} edge separator`);
      assert.ok(!seps.some((s, i) => s && seps[i + 1]), `${app}/${m.id} double separator`);
    }
  }
});

test('unhandled id is shown disabled while the rest stay enabled', () => {
  const sim = menusFor(spec, 'sim', { handled: (id) => id !== 'file.report' });
  assert.equal(find(sim, 'file.report').enabled, false);
  assert.equal(find(sim, 'file.export.csv').enabled, true);
});

test('nextIndex skips separators and disabled items and wraps', () => {
  const items = [{ id: 'a', enabled: true }, { separator: true }, { id: 'b', enabled: false }, { id: 'c', enabled: true }];
  assert.equal(nextIndex(items, 0, 1), 3);
  assert.equal(nextIndex(items, 3, 1), 0);
  assert.equal(nextIndex(items, 0, -1), 3);
  assert.equal(nextIndex(items, -1, 1), 0); // 아무것도 선택 안 된 상태에서 ↓
});
