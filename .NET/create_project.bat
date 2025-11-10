@echo off
if "%1" == "" (
    set /p projectName="プロジェクト名を入力 : "
) else (
    set projectName=%1
)

if not exist "%projectName%" (
    dotnet new console -o "%projectName%"
    echo @echo off >> "%projectName%\run.bat"
    echo cd /d %%~dp0 >> "%projectName%\run.bat"
    echo dotnet run >> "%projectName%\run.bat"
    echo 作成完了
) else (
    echo プロジェクトは作成済みです
)

pause > nul