@echo off
setlocal
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%"
powershell -ExecutionPolicy Bypass -File "tools\build_addon.ps1" %*
popd
endlocal
