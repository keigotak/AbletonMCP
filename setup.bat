@echo off
echo.
echo ========================================================
echo        Ableton Agent - Setup with uv
echo ========================================================
echo.

echo Creating virtual environment...
python -m uv venv
echo.

echo Installing packages...
python -m uv pip install python-osc rich mcp
echo.

echo [OK] Setup complete!
echo.
echo ========================================================
echo NEXT STEPS
echo ========================================================
echo.
echo 1. Copy claude_desktop_config.json to Claude folder:
echo    copy claude_desktop_config.json %%APPDATA%%\Claude\
echo.
echo 2. Restart Claude Desktop
echo.
echo 3. Type "Connect to Ableton" in Claude Desktop
echo.
pause
