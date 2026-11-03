@echo off
setlocal EnableExtensions

rem Installs only the inert, safe spawn-menu template. This does not add F2 UI or spawn items.
set "SOURCE=%~dp0..\mods\DevSpawnMenu\cheats\277178B7DBA1B6D4.txt"

if not exist "%SOURCE%" (
  echo ERROR: Template file is missing:
  echo   "%SOURCE%"
  exit /b 1
)

set "TARGET=%~1"
if not defined TARGET set /p "TARGET=Enter the folder containing totk.exe: "
if not defined TARGET (
  echo ERROR: No install folder was provided.
  exit /b 1
)

if not exist "%TARGET%\totk.exe" if not exist "%TARGET%\totk" (
  echo ERROR: Could not find totk.exe or totk in:
  echo   "%TARGET%"
  echo Pass the game install folder, not the executable path.
  exit /b 1
)

set "DEST=%TARGET%\mods\DevSpawnMenu\cheats"
if not exist "%DEST%" mkdir "%DEST%" || exit /b 1
copy /Y "%SOURCE%" "%DEST%\277178B7DBA1B6D4.txt" >nul
if errorlevel 1 (
  echo ERROR: Could not copy the template.
  exit /b 1
)

echo.
echo Installed the inert template at:
echo   "%DEST%\277178B7DBA1B6D4.txt"
echo.
echo IMPORTANT: This is not a working cheat or spawn menu. It contains no item-spawn writes.
echo F2 UI and item spawning require runtime code and a verified inventory grant implementation.
echo Remove the DevSpawnMenu folder if you do not want the template installed.
exit /b 0
