@echo off
setlocal

:: ===== Check Administrator =====
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Elevating to Administrator...
    powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: ===== Get script folder =====
set "TARGET_DIR=%~dp0"
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"

echo ========================================
echo   Add current folder to SYSTEM PATH
echo ========================================
echo.
echo Folder: %TARGET_DIR%
echo.

:: ===== Use PowerShell to modify registry directly (bypasses setx 1024 limit) =====
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$dir = $env:TARGET_DIR;" ^
  "Write-Host \"Target: $dir\";" ^
  "$key = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment';" ^
  "$current = (Get-ItemProperty $key -Name Path).Path;" ^
  "Write-Host \"Current PATH length: $($current.Length) chars\";" ^
  "if ($current -like \"*$dir*\") {" ^
  "    Write-Host '[INFO] Already in system PATH, skipped.';" ^
  "} else {" ^
  "    $newPath = $current + ';' + $dir;" ^
  "    Set-ItemProperty -Path $key -Name Path -Value $newPath -Type ExpandString;" ^
  "    Write-Host \"[OK] Added to system PATH.\";" ^
  "    Write-Host \"New PATH length: $($newPath.Length) chars\";" ^
  "    Add-Type -Namespace Win32 -Name Native -MemberDefinition '[DllImport(\"user32.dll\", SetLastError=true, CharSet=CharSet.Auto)] public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);';" ^
  "    $HWND_BROADCAST = [IntPtr]0xffff; $WM_SETTINGCHANGE = 0x1a;" ^
  "    $result = [UIntPtr]::Zero;" ^
  "    [Win32.Native]::SendMessageTimeout($HWND_BROADCAST, $WM_SETTINGCHANGE, [UIntPtr]::Zero, 'Environment', 2, 5000, [ref]$result) | Out-Null;" ^
  "    Write-Host '[OK] Broadcast WM_SETTINGCHANGE done.';" ^
  "}"

echo.
echo ========================================
echo   Done. Open a NEW CMD to verify:
echo   echo %%PATH%%
echo ========================================
pause
