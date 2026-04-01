@echo off
echo ===================================================
echo      Construction Material Chatbot Launcher
echo ===================================================
echo.

echo [1/3] Starting Backend Server...
start "Chatbot Backend" cmd /k "cd backend && call venv\Scripts\activate && uvicorn main:app --reload"

echo [2/3] Starting Frontend Server...
start "Chatbot Frontend" cmd /k "cd frontend && npm run dev"

echo [3/3] Opening Browser...
timeout /t 5 >nul
start http://localhost:3000

echo.
echo ===================================================
echo      All systems go! Don't close this window.
echo ===================================================
pause
