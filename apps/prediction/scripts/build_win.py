"""MAPS Windows build script: make_ico -> PyInstaller -> electron-builder"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

def run(cmd, **kwargs):
    print(f"\n>>> {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, shell=isinstance(cmd, str), **kwargs)
    if result.returncode != 0:
        print(f"ERROR: command failed (exit {result.returncode})")
        sys.exit(result.returncode)

print("=" * 50)
print("MAPS - Windows Build")
print("=" * 50)

# Step 1: icon.ico
print("\n[1/3] Generating icon.ico...")
run([sys.executable, "scripts/make_ico.py"])

# Step 2: PyInstaller
print("\n[2/3] PyInstaller packaging...")
run([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])
run([
    sys.executable, "-m", "PyInstaller",
    "main.py",
    "--name", "main_app",
    "--onedir",
    "--windowed",
    "--distpath", "dist_python",
    "--workpath", "build_pyinstaller",
    "--add-data", "src;src",
    "--add-data", "assets;assets",
    "--add-data", "models;models",
    "--hidden-import", "PyQt6.sip",
    "--hidden-import", "sklearn.utils._typedefs",
    "--hidden-import", "sklearn.neighbors._partition_nodes",
    "--hidden-import", "sklearn.tree._utils",
    "--collect-all", "xgboost",
    "--collect-all", "lightgbm",
    "--collect-all", "catboost",
    "--exclude-module", "PyQt5",
    "--exclude-module", "torch",
    "--exclude-module", "torchvision",
    "--exclude-module", "cv2",
    "--icon", "assets/icon.ico",
    "--noconfirm",
])

# Step 3: electron-builder
print("\n[3/3] electron-builder...")
run("npm run build:win")

print("\n" + "=" * 50)
print("Done! Installer: dist_electron/")
print("=" * 50)
