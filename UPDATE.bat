@echo off
chcp 65001 >nul

if not defined WT_SESSION (
    wt.exe -p "Command Prompt" cmd /k "%~f0"
    exit /b
)

set "ZIP_NAME=olx_parser-master.zip"
set "CURRENT_DIR=%~dp0"
set "ZIP_FILE=%CURRENT_DIR%%ZIP_NAME%"
set "TEMP_DIR=%CURRENT_DIR%__tmp_repo_unpack"

if not exist "%ZIP_FILE%" (
    echo ⚠️  Файл "%ZIP_NAME%" не найден в текущей папке.
    echo.
    pause
    exit
)

powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%TEMP_DIR%' -Force"

if not exist "%TEMP_DIR%" (
    echo ⚠️  Не удалось распаковать архив.
    pause
    exit
)

for /D %%D in ("%TEMP_DIR%\*") do (
    xcopy "%%~fD\*" "%CURRENT_DIR%" /E /Y /I >nul
)

rmdir /S /Q "%TEMP_DIR%"
del /F /Q "%ZIP_FILE%"

exit