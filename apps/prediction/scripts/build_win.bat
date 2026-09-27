@echo off
setlocal EnableDelayedExpansion
echo ============================================
echo  MAPS - Windows 배포 빌드
echo ============================================
echo.

REM ── Python 실행 파일 찾기
set PYTHON=python
where python >nul 2>&1 || (set PYTHON=py)

REM ── 1단계: icon.ico 생성
echo [1/3] icon.ico 생성 중...
%PYTHON% scripts\make_ico.py
if errorlevel 1 ( echo 오류: icon.ico 생성 실패 && pause && exit /b 1 )
echo.

REM ── 2단계: PyInstaller로 Python 앱 패키징
echo [2/3] Python 앱 PyInstaller 패키징 중...
%PYTHON% -m pip install pyinstaller -q
pyinstaller main.py ^
  --name main_app ^
  --onedir ^
  --windowed ^
  --distpath dist_python ^
  --workpath build_pyinstaller ^
  --add-data "src;src" ^
  --add-data "assets;assets" ^
  --add-data "models;models" ^
  --hidden-import PyQt6.sip ^
  --hidden-import sklearn.utils._typedefs ^
  --hidden-import sklearn.neighbors._partition_nodes ^
  --hidden-import sklearn.tree._utils ^
  --icon assets\icon.ico ^
  --noconfirm
if errorlevel 1 ( echo 오류: PyInstaller 빌드 실패 && pause && exit /b 1 )
echo.

REM ── 3단계: electron-builder로 설치 파일 생성
echo [3/3] Electron 설치 파일 빌드 중...
call npm install --save-dev electron-builder
call npm run build:win
if errorlevel 1 ( echo 오류: electron-builder 빌드 실패 && pause && exit /b 1 )
echo.

echo ============================================
echo  완료! 설치 파일 위치: dist_electron\
echo ============================================
pause
