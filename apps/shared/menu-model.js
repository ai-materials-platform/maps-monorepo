// 메뉴 정의(menus.json)를 앱별로 거르고 키보드 이동을 계산한다 — 순수 함수, DOM 없음.
// 셸·시뮬 타이틀바(titlebar.js)와 Electron 숨김 메뉴(window-chrome.cjs)가 같이 쓴다.
// PyQt는 같은 규칙을 theme_tokens.menus_for로 구현한다.

export function menusFor(spec, app, { dev = false, handled = () => true } = {}) {
  const result = [];
  for (const menu of spec.menus) {
    const items = [];
    for (const item of menu.items) {
      if (item.separator) {
        if (items.length && !items.at(-1).separator) items.push({ separator: true });
        continue;
      }
      if (!item.apps.includes(app) || (item.devOnly && !dev)) continue;
      items.push({ ...item, enabled: !!handled(item.id) });
    }
    while (items.length && items.at(-1).separator) items.pop();
    if (items.length) result.push({ id: menu.id, label: menu.label, items });
  }
  return result;
}

// 구분선·비활성 항목을 건너뛰고 순환한다. 고를 항목이 없으면 current를 그대로 돌려준다.
export function nextIndex(items, current, delta) {
  const n = items.length;
  for (let step = 1; step <= n; step += 1) {
    const i = (((current + delta * step) % n) + n) % n;
    if (!items[i].separator && items[i].enabled !== false) return i;
  }
  return current;
}
