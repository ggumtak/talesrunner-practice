@echo off
chcp 65001 > nul
title 업데이트 중...

echo.
echo ========================================
echo   최신 버전으로 업데이트 중...
echo ========================================
echo.

cd /d "%~dp0"

:: Git 확인
git --version >nul 2>&1
if errorlevel 1 (
    echo [!] Git이 설치되어 있지 않아 자동 업데이트가 불가능합니다.
    echo     수동으로 GitHub에서 다시 다운로드해주세요:
    echo     https://github.com/ggumtak/talesrunner-practice
    echo.
    pause
    exit /b 1
)

:: 업데이트 실행
echo 서버에서 최신 버전 다운로드 중...
git pull origin main

echo.
echo ========================================
echo   업데이트 완료!
echo   "★ 여기를 더블클릭해서 실행.bat" 를 실행하세요
echo ========================================
echo.
pause
