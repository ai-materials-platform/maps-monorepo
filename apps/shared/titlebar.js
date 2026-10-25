// 셸·시뮬(Electron) 공통 타이틀바 — PyQt CustomTitleBar와 같은 모양(높이 30px, 로고 24px, 메뉴 11px 굵게).
// 창 버튼(─ □ ✕)은 Electron titleBarOverlay(Windows 기본)가 그리므로 오른쪽 138px을 비워 둔다.
import { menusFor, nextIndex } from './menu-model.js';

const LOGO = 'data:image/svg+xml;utf8,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">' +
  '<circle cx="40" cy="40" r="38" fill="#0e1c40"/>' +
  '<g fill="none" stroke="#4a9eff" stroke-width="1.8" opacity="0.9">' +
  '<ellipse cx="40" cy="40" rx="26" ry="9"/>' +
  '<ellipse cx="40" cy="40" rx="26" ry="9" transform="rotate(60 40 40)"/>' +
  '<ellipse cx="40" cy="40" rx="26" ry="9" transform="rotate(120 40 40)"/></g>' +
  '<circle cx="40" cy="40" r="5.8" fill="#4a9eff"/><circle cx="40" cy="40" r="2.7" fill="#fff"/></svg>'
);

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
};

export function mountTitlebar(host, { app, spec, title = '', dev = false, handled = () => true, onAction, checkedId = null }) {
  const menus = menusFor(spec, app, { dev, handled });
  const bar = el('div', 'maps-titlebar');
  const logo = el('img', 'maps-logo');
  logo.src = LOGO;
  logo.alt = '';
  const menubar = el('div', 'maps-menubar');
  const titleEl = el('div', 'maps-title', title);
  bar.append(logo, menubar, titleEl, el('div', 'maps-overlay-gap'));

  let openIndex = -1;
  let active = -1;
  let pop = null;
  const buttons = menus.map((menu, i) => {
    const b = el('button', 'maps-menu-btn', menu.label);
    b.type = 'button';
    b.addEventListener('mousedown', (e) => e.preventDefault()); // 포커스를 뺏지 않아야 복사·붙여넣기가 입력창에 간다
    b.addEventListener('click', () => (openIndex === i ? close() : open(i)));
    b.addEventListener('mouseenter', () => { if (openIndex !== -1 && openIndex !== i) open(i); });
    menubar.append(b);
    return b;
  });

  function run(item) {
    if (!item || item.separator || !item.enabled) return;
    close();
    onAction?.(item.id);
  }

  function highlight(i) {
    active = i;
    pop?.querySelectorAll('.maps-menu-item').forEach((n) => n.classList.toggle('is-active', Number(n.dataset.index) === i));
  }

  function open(i) {
    close();
    openIndex = i;
    buttons[i].classList.add('is-open');
    pop = el('div', 'maps-menu-pop');
    pop.setAttribute('role', 'menu');
    pop.addEventListener('mousedown', (e) => e.preventDefault());
    menus[i].items.forEach((item, idx) => {
      if (item.separator) { pop.append(el('div', 'maps-menu-sep')); return; }
      const row = el('div', 'maps-menu-item' + (item.enabled ? '' : ' is-disabled'));
      row.setAttribute('role', 'menuitem');
      row.dataset.index = String(idx);
      row.append(el('span', 'maps-menu-check', item.id === checkedId ? '✓' : ''), el('span', 'maps-menu-label', item.label),
        el('span', 'maps-menu-shortcut', item.shortcut || ''));
      row.addEventListener('mouseenter', () => item.enabled && highlight(idx));
      row.addEventListener('click', () => run(item));
      pop.append(row);
    });
    const r = buttons[i].getBoundingClientRect();
    pop.style.left = `${r.left}px`;
    pop.style.top = `${r.bottom}px`;
    document.body.append(pop);
    active = -1;
  }

  function close() {
    if (openIndex !== -1) buttons[openIndex].classList.remove('is-open');
    openIndex = -1;
    active = -1;
    pop?.remove();
    pop = null;
  }

  function onKey(e) {
    if (openIndex === -1) return;
    const items = menus[openIndex].items;
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowDown') highlight(nextIndex(items, active, 1));
    else if (e.key === 'ArrowUp') highlight(nextIndex(items, active === -1 ? 0 : active, -1));
    else if (e.key === 'ArrowRight') open((openIndex + 1) % menus.length);
    else if (e.key === 'ArrowLeft') open((openIndex - 1 + menus.length) % menus.length);
    else if (e.key === 'Enter' && active !== -1) run(items[active]);
    else return;
    e.preventDefault();
  }
  const onDown = (e) => { if (pop && !pop.contains(e.target) && !menubar.contains(e.target)) close(); };

  document.addEventListener('keydown', onKey, true);
  document.addEventListener('mousedown', onDown, true);
  window.addEventListener('blur', close);
  host.replaceChildren(bar);

  return {
    setTitle: (text) => { titleEl.textContent = text; },
    close,
    destroy() {
      close();
      document.removeEventListener('keydown', onKey, true);
      document.removeEventListener('mousedown', onDown, true);
      window.removeEventListener('blur', close);
      bar.remove();
    },
  };
}
