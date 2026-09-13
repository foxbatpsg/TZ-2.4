@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem ============================================================
rem   push.bat — обёртка над push.sh для Windows
rem   https://github.com/foxbatpsg/TZ-2.4
rem
rem   Зачем: push.sh чинит сломанный ref-namespace .git/refs/cline/,
rem   из-за которого после push git status врёт "upstream is gone".
rem   Двойной щелчок по .sh в Windows не работает — этот батник
rem   вызывает bash и прокидывает все аргументы.
rem
rem   Использование:
rem     push                     - push текущей ветки
rem     push -m "сообщение"      - add + commit + push + починка ref
rem ============================================================

setlocal

rem --- шаг 1: найти bash ---
rem ВАЖНО: в C:\Program Files\Git\cmd лежит только git.exe, bash.exe там НЕТ.
rem Поэтому сначала пробуем `where`, затем явные пути Git for Windows.
set "BASH="

for /f "delims=" %%i in ('where bash 2^>nul') do (
    if not defined BASH set "BASH=%%i"
)

if not defined BASH if exist "%ProgramFiles%\Git\bin\bash.exe" set "BASH=%ProgramFiles%\Git\bin\bash.exe"
if not defined BASH if exist "%ProgramFiles%\Git\usr\bin\bash.exe" set "BASH=%ProgramFiles%\Git\usr\bin\bash.exe"
if not defined BASH if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" set "BASH=%ProgramFiles(x86)%\Git\bin\bash.exe"
if not defined BASH if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" set "BASH=%LOCALAPPDATA%\Programs\Git\bin\bash.exe"

if not defined BASH (
    echo.
    echo ОШИБКА: bash не найден.
    echo Установите Git for Windows: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Push для ТЗ 2.4
echo   https://github.com/foxbatpsg/TZ-2.4
echo ========================================
echo.

rem --- шаг 2: проверить наличие push.sh ---
if not exist "%~dp0push.sh" (
    echo ОШИБКА: не найден push.sh рядом с этим батником.
    echo Ожидался: %~dp0push.sh
    echo.
    pause
    exit /b 1
)

rem --- шаг 3: вызвать push.sh со всеми аргументами ---
"%BASH%" "%~dp0push.sh" %*

set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
    echo ========================================
    echo   ОШИБКА: push завершился с кодом %RC%
    echo ========================================
    pause
    exit /b %RC%
)

echo ========================================
echo   Готово! Изменения на GitHub.
echo ========================================
echo.
pause
exit /b 0
