@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ======================================
echo   Установка LaTeX-пакетов MiKTeX
echo ======================================
echo.

if not exist "latex_packages.txt" (
    echo Файл latex_packages.txt не найден в папке скрипта.
    pause
    exit /b 1
)

echo Обновляю базу пакетов MiKTeX...
miktex packages update-package-database
if errorlevel 1 (
    echo Предупреждение: не удалось обновить базу. Некоторые пакеты могут не установиться.
)
echo.

echo Устанавливаю пакеты из latex_packages.txt...
for /f "usebackq delims=" %%p in ("latex_packages.txt") do (
    if not "%%p"=="" (
        echo Установка %%p...
        miktex packages install %%p
        if errorlevel 1 (
            echo [ПРОПУЩЕНО] Пакет "%%p" уже установлен или недоступен.
        )
    )
)
echo.
echo Установка LaTeX-пакетов завершена.

:: Проверка lualatex (если нужно)
lualatex --version >nul 2>&1
if errorlevel 1 (
    echo ВНИМАНИЕ: lualatex не найден в PATH.
)

pause