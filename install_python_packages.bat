@echo off
chcp 65001 >nul
echo ======================================
echo    Установка окружения для altidoc
echo ======================================
echo.

:: Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python не найден.
    echo Пожалуйста, установите Python 3.8 или новее:
    echo   https://www.python.org/downloads/
    pause
    exit /b 1
)
echo Python найден.

:: Создание виртуального окружения (если ещё нет)
if not exist "venv\" (
    echo Создаю виртуальное окружение в папке venv...
    python -m venv venv
)

:: Активация и установка пакетов
echo Устанавливаю зависимости...
venv\Scripts\python.exe -m pip install --upgrade pip -q
venv\Scripts\pip.exe install -r requirements.txt -q
if errorlevel 1 (
    echo Ошибка при установке зависимостей.
    pause
    exit /b 1
)
echo Зависимости установлены...

:: Проверка lualatex (если программа должна формировать PDF)
lualatex --version >nul 2>&1
if errorlevel 1 (
    echo ВНИМАНИЕ: lualatex не найден в переменных PATH!
    echo Если вам нужно формировать PDF-документы, установите MiKTeX:
    echo   https://miktex.org/download
)
echo.
echo Установка завершена!
echo Теперь запускайте программу через run.vbs
pause