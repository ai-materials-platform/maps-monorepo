const checks = [
  ['simulation-backend 8765', 'http://127.0.0.1:8765/health'],
  ['simulation-vite 5173', 'http://127.0.0.1:5173/'],
];
for (const [name, url] of checks) {
  try {
    const res = await fetch(url);
    const text = await res.text();
    console.log(name, '->', res.status, text.slice(0, 100).replace(/\s+/g, ' '));
  } catch (e) {
    console.log(name, '-> FAIL:', e.message);
  }
}
