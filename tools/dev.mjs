/* MAPS 원커맨드 실행: Flask(:5000) + 셸(Electron). Ctrl+C로 전체 종료. */
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');
const isWindows = process.platform === 'win32';

const children = [];

function run(command, args, options = {}) {
  const child = spawn(command, args, {
    stdio: 'inherit',
    shell: isWindows,
    cwd: rootDir,
    ...options,
  });
  children.push(child);
  child.on('exit', (code) => {
    console.log(`[dev] ${command} ${args.join(' ')} exited (${code}) — shutting down`);
    shutdown();
    process.exit(code ?? 0);
  });
  return child;
}

function shutdown() {
  for (const child of children) {
    try {
      if (!child.killed) child.kill();
    } catch (_) {}
  }
}

process.on('SIGINT', () => { shutdown(); process.exit(0); });
process.on('SIGTERM', () => { shutdown(); process.exit(0); });

const python = process.env.AI_MATERIALS_PYTHON || 'python';
run(python, ['apps/prediction/src/api/server.py']);
run(isWindows ? 'npm.cmd' : 'npm', ['run', 'dev:shell']);
