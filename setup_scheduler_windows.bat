@echo off
REM ============================================================
REM 나라장터 입찰 모니터링 - Windows 작업 스케줄러 등록 스크립트
REM 관리자 권한으로 실행하세요
REM ============================================================

set TASK_NAME=나라장터입찰모니터링
set PYTHON_PATH=python
set SCRIPT_PATH=%~dp0main.py
set LOG_PATH=%~dp0scheduler.log

echo 작업 스케줄러에 등록 중...

schtasks /create /tn "%TASK_NAME%" /tr "%PYTHON_PATH% %SCRIPT_PATH% --now" /sc daily /st 09:30 /f /rl highest

if %errorlevel% == 0 (
    echo.
    echo ✅ 성공! 매일 오전 09:30에 자동 실행됩니다.
    echo.
    echo 작업 이름: %TASK_NAME%
    echo 실행 파일: %SCRIPT_PATH%
    echo.
    echo 작업 스케줄러 확인: Windows 검색 → "작업 스케줄러" 검색
) else (
    echo.
    echo ❌ 등록 실패. 관리자 권한으로 실행했는지 확인하세요.
)

pause
