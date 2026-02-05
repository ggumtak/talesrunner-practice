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
) else (
    echo [2/4] 환경 로딩 중...
    call venv\Scripts\activate.bat
)

echo [3/4] 브라우저 열기...

:: PowerShell로 3초 후 브라우저 열기 (창 없이)
powershell -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://localhost:8000'"

echo [4/4] 서버 시작 중...
echo.
echo ========================================
echo   준비 완료!
echo   종료: 이 창 닫기 또는 트레이 아이콘 우클릭 - 종료
echo ========================================
echo.

:: 서버 실행 (pythonw가 있으면 사용, 없으면 python 사용)
python main.py
