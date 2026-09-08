@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo   Git Push для ТЗ 2.4
echo   https://github.com/foxbatpsg/TZ-2.4
echo ========================================
echo.

set /p "REPO_NAME=Введите имя (описание изменений): "

if "%REPO_NAME%"=="" (
    echo Ошибка: имя не может быть пустым.
    pause
    exit /b 1
)

echo.
echo ==^> Добавление всех файлов в индекс...
git add -A
echo.

echo ==^> Создание коммита: %REPO_NAME%
git commit -m "%REPO_NAME%"
if errorlevel 1 (
    echo.
    echo Внимание: не удалось создать коммит ^((возможно, нет изменений^)
    echo.
)

echo.
echo ==^> Отправка изменений на GitHub...
git push
if errorlevel 1 (
    echo.
    echo Ошибка: не удалось выполнить push.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Готово! Изменения отправлены на GitHub.
echo ========================================
echo.
pause