@echo off
setlocal

echo.
echo  ============================================================
echo   CiteRAG — Local Development Startup
echo  ============================================================
echo.

REM --- Step 1: Start backing services via Docker Compose ---
echo [1/3] Starting Qdrant, MongoDB, Elasticsearch, and Ollama via Docker...
docker-compose up -d qdrant mongo elasticsearch ollama
if %ERRORLEVEL% neq 0 (
    echo.
    echo  ERROR: docker-compose failed. Make sure Docker Desktop is running.
    pause
    exit /b 1
)

echo.
echo [2/3] Waiting 10 seconds for services to become ready...
timeout /t 10 /nobreak >nul

REM --- Step 2: Activate virtual environment ---
echo [3/3] Starting FastAPI backend (http://localhost:8000)...
echo.
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo  WARNING: venv not found. Run:  python -m venv venv ^& venv\Scripts\pip install -r requirements.txt
)

echo  * Frontend : http://localhost:8000/frontend/index.html
echo  * API docs : http://localhost:8000/docs
echo  * Health   : http://localhost:8000/health
echo.
echo  Press CTRL+C to stop the backend.
echo.

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
