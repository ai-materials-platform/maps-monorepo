"""MAPS Windows build: icon -> 시뮬 프론트(vite) -> PyInstaller(scripts/maps.spec) -> electron-builder(셸)"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # apps/prediction
APPS = os.path.dirname(ROOT)
SHELL_DIR = os.path.join(APPS, "shell")
SIM_DIR = os.path.join(APPS, "simulation")
os.chdir(ROOT)


def run(cmd, cwd=None):
    print(f"\n>>> {' '.join(cmd) if isinstance(cmd, list) else cmd}  (cwd={cwd or ROOT})")
    result = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=cwd)
    if result.returncode != 0:
        print(f"ERROR: command failed (exit {result.returncode})")
        sys.exit(result.returncode)


print("=" * 50)
print("MAPS - Windows Build")
print("=" * 50)

print("\n[1/4] Generating icon.ico...")
run([sys.executable, "scripts/make_ico.py"])
# 셸 설치 파일(NSIS)도 같은 로고를 쓴다 — 셸 assets엔 png만 있어 ico를 복사
shutil.copyfile(os.path.join(ROOT, "assets", "icon.ico"), os.path.join(SHELL_DIR, "assets", "icon.ico"))

print("\n[2/4] Simulation frontend (vite build)...")
run("npm run build", cwd=SIM_DIR)

print("\n[3/4] PyInstaller (main_app + prediction_api + simulation_api)...")
# 클린 venv에서 빌드한다: 전역 Python엔 무관한 패키지(pymc·streamlit·jupyter 등)가 깔려 있어
# 선택 import로 번들에 딸려 들어온다 (전역 빌드 2.5GB). requirements.txt만 설치해 그 경로를 끊는다.
venv_dir = os.path.join(ROOT, "build_pyinstaller", "venv")
venv_py = os.path.join(venv_dir, "Scripts", "python.exe")
if not os.path.exists(venv_py):
    run([sys.executable, "-m", "venv", venv_dir])
run([venv_py, "-m", "pip", "install", "-q", "--upgrade", "pip"])
run([venv_py, "-m", "pip", "install", "-q", "-r", "requirements.txt", "pyinstaller"])
run([
    venv_py, "-m", "PyInstaller", "scripts/maps.spec",
    # 셸 package.json extraResources가 apps/shell/dist_python/main_app 를 집어간다
    "--distpath", os.path.join(SHELL_DIR, "dist_python"),
    "--workpath", "build_pyinstaller",
    "--noconfirm",
])

print("\n[4/4] electron-builder...")
run("npm run build:win", cwd=SHELL_DIR)

print("\n" + "=" * 50)
print(f"Done! Installer: {os.path.join(SHELL_DIR, 'dist_electron')}")
print("=" * 50)
