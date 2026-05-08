@echo off
chcp 65001 >nul
set MIKTEX=miktex

for /f "usebackq delims=" %%p in ("latex_packages.txt") do (
    echo Установка %%p...
    "%MIKTEX%" --yes --install-package %%p
)
echo Готово.