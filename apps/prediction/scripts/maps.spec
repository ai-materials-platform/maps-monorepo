# -*- mode: python ; coding: utf-8 -*-
# MAPS Python 번들: 실행 파일 3개가 _internal 하나를 공유한다 (대형 ML 의존성 1벌만).
#   main_app.exe        PyQt 예측 앱
#   prediction_api.exe  Flask :5000 (셸이 띄움 — 시뮬 커스텀 모델·웹 저장소)
#   simulation_api.exe  시뮬 백엔드 :8765 (셸이 띄움)
# 빌드: python scripts/build_win.py
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

APP = os.path.abspath(os.path.join(SPECPATH, ".."))  # apps/prediction
SIM_BACKEND = os.path.abspath(os.path.join(APP, "..", "simulation", "backend"))
ICON = os.path.join(APP, "assets", "icon.ico")
sys.path.insert(0, APP)  # collect_submodules("src...")용

datas = [
    (os.path.join(APP, "src"), "src"),
    (os.path.join(APP, "assets"), "assets"),
    (os.path.join(APP, "models"), "models"),
]
binaries = []
hiddenimports = [
    "PyQt6.sip",
    "sklearn.utils._typedefs",
    "sklearn.neighbors._partition_nodes",
    "sklearn.tree._utils",
]
for pkg in ("xgboost", "lightgbm", "catboost"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
# 시뮬 백엔드는 src.engine을 동적 import하고, 피클 복원에도 엔진 클래스가 필요하다
engine_modules = collect_submodules("src.engine")
excludes = ["PyQt5", "torch", "torchvision", "cv2"]


def analysis(script, extra_hidden=(), with_data=False):
    return Analysis(
        [script],
        pathex=[APP],
        binaries=binaries if with_data else [],
        datas=datas if with_data else [],
        hiddenimports=hiddenimports + list(extra_hidden),
        excludes=excludes,
        noarchive=False,
    )


a_app = analysis(os.path.join(APP, "main.py"), with_data=True)
a_api = analysis(os.path.join(APP, "src", "api", "server.py"), engine_modules)
a_sim = analysis(os.path.join(SIM_BACKEND, "simulation_server.py"), engine_modules)


def exe(a, name, console):
    return EXE(
        PYZ(a.pure),
        a.scripts,
        [],
        exclude_binaries=True,
        name=name,
        console=console,  # API는 콘솔 빌드 — 셸이 숨김으로 띄우고 stdout을 서비스 로그로 받는다
        icon=ICON,
    )


coll = COLLECT(
    exe(a_app, "main_app", console=False), a_app.binaries, a_app.datas,
    exe(a_api, "prediction_api", console=True), a_api.binaries, a_api.datas,
    exe(a_sim, "simulation_api", console=True), a_sim.binaries, a_sim.datas,
    name="main_app",
)
