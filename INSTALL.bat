@echo off

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv

    echo Activating virtual environment...
    call .venv\Scripts\activate
    echo.

    echo Installing dependencies...
    pip install -r requirements.txt
    echo.
)

echo Required dependencies installed
pause