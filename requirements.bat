@echo off
REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python non è installato. Scaricalo da https://www.python.org/downloads/
    pause
    exit /b
)

REM Create a virtual environment
echo Creazione di un ambiente virtuale...
python -m venv venv

REM Activate the virtual environment
call venv\Scripts\activate

REM Upgrade pip
echo Aggiornamento di pip...
python -m pip install --upgrade pip

REM Install required packages
echo Installazione dei pacchetti richiesti...
pip install pygame

REM Install additional libraries
pip install random

REM Finish
echo Installazione completata! Per eseguire lo script, attiva l'ambiente virtuale con:
echo call venv\Scripts\activate
pause
exit
