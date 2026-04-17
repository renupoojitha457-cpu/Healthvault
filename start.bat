@echo off
echo ==========================================
echo     HealthVault+ Startup (Windows)
echo ==========================================
cd /d "%~dp0backend"

echo Installing Python packages...
pip install fastapi uvicorn sqlalchemy python-jose[cryptography] passlib[bcrypt] python-multipart python-dotenv pydantic[email] -q

echo.
echo Starting API on http://localhost:8000
echo Open frontend\index.html in your browser
echo Press Ctrl+C to stop.
echo ==========================================

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
