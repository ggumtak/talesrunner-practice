@echo off
chcp 65001 > nul
title TR Tracker

echo.
echo ========================================
echo   테일즈런너 연습 트래커 시작 중...
echo ========================================
echo.

:: Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다!
    echo.
    echo Python 설치 방법:
    echo 1. https://www.python.org/downloads/ 접속
    echo 2. "Download Python" 버튼 클릭
    echo 3. 설치 시 "Add Python to PATH" 체크 필수!
    echo.
    pause
    exit /b 1
)

echo [1/4] Python 확인 완료!

:: src/backend 폴더로 이동
cd /d "%~dp0src\backend"

:: 가상환경 확인/생성
if not exist "venv" (
    echo [2/4] 첫 실행: 환경 설정 중... (1-2분 소요)
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet
    pip install pystray pillow --quiet
) else (
    echo [2/4] 환경 로딩 중...
    call venv\Scripts\activate.bat
)

echo [3/4] 브라우저 열기...

:: 3초 후 브라우저 자동 열기 (백그라운드)
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

echo [4/4] 서버 시작 중...
echo.
echo ========================================
echo   준비 완료! (이 창은 최소화됩니다)
echo   종료하려면 트레이 아이콘 우클릭 - 종료
echo ========================================
echo.

:: 2초 후 이 창 최소화
timeout /t 2 /nobreak >nul
powershell -window minimized -command ""

:: 서버 실행
python main.py
