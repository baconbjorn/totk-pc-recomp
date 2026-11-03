@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

if not exist "%SCRIPT_DIR%cheats" mkdir "%SCRIPT_DIR%cheats"

if not exist "%SCRIPT_DIR%README.md" (
    > "%SCRIPT_DIR%README.md" (
        echo # DevSpawnMenu
        echo.
        echo This is a safe dev-only scaffold.
        echo.
        echo The requested F2 item-spawn flow requires a verified in-game hook that this repo does not contain.
        echo This batch file only creates the mod folder layout and a non-functional placeholder cheat file.
        echo.
        echo Place this folder under mods/ next to totk.exe.
    )
)

if not exist "%SCRIPT_DIR%cheats\277178B7DBA1B6D4.txt" (
    > "%SCRIPT_DIR%cheats\277178B7DBA1B6D4.txt" (
        echo [Spawn menu placeholder]
        echo ; This file is intentionally inert.
        echo ; No real item-spawn hook is present in this repo.
        echo ; It only keeps the mod folder valid for TotK Recomp's mod layout.
    )
)

echo.
echo DevSpawnMenu scaffold created.
echo Folder: %SCRIPT_DIR%
echo Expected layout: mods\DevSpawnMenu\cheats\277178B7DBA1B6D4.txt

echo.
echo This is a safe placeholder only. It does not modify game memory or spawn items.
choice /C CN /M "Close? [C] Continue / [N] No" >nul 2>&1
