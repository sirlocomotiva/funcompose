@echo off
REM GameManager launcher - Windows (Docker Desktop)
cd /d "%~dp0"

docker info >nul 2>&1
if errorlevel 1 (
  echo ❌ Docker is not running. Start Docker Desktop and try again.
  pause
  exit /b 1
)

if not exist .env copy .env.example .env >nul

echo 🚀 Starting GameManager...
docker compose up -d --build
if errorlevel 1 (
  echo Failed to start. See errors above.
  pause
  exit /b 1
)

echo.
echo ✅ Done!
echo    Web UI : http://localhost:5173
echo    API    : http://localhost:8000/docs
pause
