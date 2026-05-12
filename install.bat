@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ======================================
echo    Установка окружения для altidoc
echo ======================================
echo.

:: ---------- Часть 1: Python и виртуальное окружение ----------
python --version >nul 2>&1
if errorlevel 1 (
    echo Python не найден.
    echo Пожалуйста, установите Python 3.8 или новее:
    echo   https://www.python.org/downloads/
    pause
    exit /b 1
)
echo Python найден.

if not exist "venv\" (
    echo Создаю виртуальное окружение в папке venv...
    python -m venv venv
) else (
    echo Виртуальное окружение уже существует.
)

echo Устанавливаю Python-зависимости из requirements.txt...
venv\Scripts\python.exe -m pip install --upgrade pip -q
venv\Scripts\pip.exe install -r requirements.txt -q
if errorlevel 1 (
    echo Ошибка при установке зависимостей.
    pause
    exit /b 1
)
echo Готово: Python-зависимости установлены.

:: ---------- Часть 2: LaTeX-пакеты (MiKTeX) ----------
if exist "latex_packages.txt" (
    echo.
    echo ---------------------------------------------------
    echo Обнаружен latex_packages.txt — установка LaTeX-пакетов
    echo ---------------------------------------------------
    echo Обновление базы пакетов MiKTeX...
    miktex packages update-package-database
    if errorlevel 1 (
        echo Предупреждение: не удалось обновить базу пакетов.
    )
    echo.
    echo Установка пакетов...
    for /f "usebackq delims=" %%p in ("latex_packages.txt") do (
        if not "%%p"=="" (
            echo Установка %%p...
            miktex packages install %%p >nul 2>&1
            if errorlevel 1 (
                echo [ПРОПУЩЕНО] Пакет "%%p" уже установлен или недоступен.
            ) else (
                echo [OK] %%p установлен.
            )
        )
    )
    echo.
    echo Установка LaTeX-пакетов завершена.
) else (
    echo.
    echo Файл latex_packages.txt не найден — пропускаю установку LaTeX-пакетов.
)

:: Общая проверка lualatex
echo.
lualatex --version >nul 2>&1
if errorlevel 1 (
    echo ВНИМАНИЕ: lualatex не найден в переменных PATH!
    echo Если вам нужно формировать PDF-документы, установите MiKTeX:
    echo   https://miktex.org/download
)

echo.
echo ======================================
echo   Установка завершена!
echo   Запускайте программу через run.vbs
echo ======================================
pause