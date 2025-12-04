@echo off
REM Senior Scraper Dashboard Launcher for Windows

echo ========================================
echo Senior Scraper Web Dashboard
echo ========================================
echo.

REM Load environment variables from wp_config.env
if exist wp_config.env (
    echo Loading environment variables...
    for /f "usebackq tokens=1,* delims==" %%a in ("wp_config.env") do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" (
            set "%%a=%%b"
        )
    )
    echo Environment loaded!
) else (
    echo WARNING: wp_config.env not found!
    echo Please create wp_config.env with your credentials.
    pause
    exit /b 1
)

echo.
echo Installing/checking Flask...
python -m pip install flask>=3.0.0 --quiet

echo.
echo Starting dashboard at http://localhost:5000
echo Press Ctrl+C to stop
echo.

cd web_interface
python app.py

pause

