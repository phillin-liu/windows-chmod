@echo off
setlocal enabledelayedexpansion

set "TARGET_DIR=%~dp0"
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"

echo ========================================
echo   Add current folder to PATH
echo ========================================
echo.
echo Folder: %TARGET_DIR%
echo.

set "FOUND=0"
for /f "tokens=2*" %%a in ('reg query HKCU\Environment /v PATH 2^>nul') do (
    echo %%b | findstr /i /c:"%TARGET_DIR%" >nul
    if !errorlevel! equ 0 set "FOUND=1"
)

if %FOUND% equ 1 (
    echo [INFO] Already in PATH, skipped.
    goto done
)

echo Adding to user PATH...
setx PATH "%PATH%;%TARGET_DIR%"

if %errorlevel% equ 0 (
    echo.
    echo [OK] Added to user PATH successfully!
    echo.
    echo NOTE: Restart CMD/PowerShell to take effect.
) else (
    echo.
    echo [FAIL] Error adding to PATH.
    echo Try running this script as Administrator.
)

:done
echo.
echo Done.
pause
