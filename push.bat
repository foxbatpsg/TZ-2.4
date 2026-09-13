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
rem   !!! ВАЖНО: в Windows есть ТРИ разных bash.exe:
rem     1. C:\Windows\System32\bash.exe        — WSL-лаунчер (НЕ подходит!)
rem     2. ...\WindowsApps\bash.exe            — WSL-стаб  (НЕ подходит!)
rem     3. C:\Program Files\Git\bin\bash.exe   — Git Bash  (НУЖЕН ЭТОТ)
rem   Если выбрать WSL-bash, он не найдёт git/awk -> код 127.
rem   Поэтому здесь мы идём по явным путям Git for Windows, а
rem   `where bash` используется лишь как последний шанс и с
rem   фильтром, отсекающим System32 и WindowsApps.
rem
rem   Использование:
rem     push                     - push текущей ветки
rem     push -m "сообщение"      - add + commit + push + починка ref
rem ============================================================

setlocal

rem --- шаг 1: найти ИМЕННО Git Bash (не WSL) ---
set "BASH="

if exist "%ProgramFiles%\Git\bin\bash.exe"            set "BASH=%ProgramFiles%\Git\bin\bash.exe"
if not defined BASH if exist "%ProgramFiles%\Git\usr\bin\bash.exe"      set "BASH=%ProgramFiles%\Git\usr\bin\bash.exe"
if not defined BASH if exist "%ProgramFiles(x86)%\Git\bin\bash.exe"     set "BASH=%ProgramFiles(x86)%\Git\bin\bash.exe"
if not defined BASH if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" set "BASH=%LOCALAPPDATA%\Programs\Git\bin\bash.exe"
if not defined BASH if exist "%USERPROFILE%\scoop\apps\git\current\bin\bash.exe" set "BASH=%USERPROFILE%\scoop\apps\git\current\bin\bash.exe"

rem Последний шанс: `where bash`, но только если путь НЕ ведёт в WSL/WindowsApps.
if not defined BASH (
    for /f "delims=" %%i in ('where bash 2^>nul') do (
        if not defined BASH (
            echo %%i | findstr /i /c:"\\System32\\" /c:"\\WindowsApps\\" >nul
            if errorlevel 1 set "BASH=%%i"
        )
    )
)

if not defined BASH (
    echo.
    echo ОШИБКА: Git Bash не найден.
    echo Установите Git for Windows: https://git-scm.com/download/win
    echo.
    echo Внимание: WSL-bash из C:\Windows\System32 не подходит —
    echo нужен именно Git Bash из состава Git for Windows.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Push для ТЗ 2.4
echo   https://github.com/foxbatpsg/TZ-2.4
echo ========================================
echo   bash: %BASH%
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
    if "%RC%"=="127" (
        echo.
        echo Код 127 = команда не найдена. Наиболее вероятная причина:
        echo выбран не тот bash. Убедитесь, что используется Git Bash,
        echo а не WSL из C:\Windows\System32.
        echo.
    )
    pause
    exit /b %RC%
)

echo ========================================
echo   Готово! Изменения на GitHub.
echo ========================================
echo.
pause
exit /b 0
