@echo off
title WarrantyBot India - Telegram
echo ========================================================
echo   WarrantyBot India - Automated Warranty Vault
echo   100% Free Telegram Bot Runner
echo ========================================================
echo.

:: Check if virtualenv exists
if not exist "venv" (
    echo [1/3] Creating Python virtual environment...
    python -m venv venv
)

echo [2/3] Activating virtual environment & installing requirements...
call venv\Scripts\activate
pip install -r requirements.txt

echo.
echo [3/3] Launching WarrantyBot India...
echo.
python main.py

pause