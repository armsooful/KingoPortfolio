#!/bin/bash
# KingoPortfolio - 백엔드/프론트엔드 서버 재시작 스크립트

PROJECT_DIR="/Users/changrim/KingoPortfolio"
VENV_DIR="$PROJECT_DIR/venv"

# 기존 백엔드 프로세스 종료
BACKEND_PIDS=$(lsof -ti :8000 2>/dev/null)
if [ -n "$BACKEND_PIDS" ]; then
  echo "[Backend] 기존 프로세스 종료 (PID: $BACKEND_PIDS)"
  kill $BACKEND_PIDS 2>/dev/null
  sleep 1
fi

# 기존 프론트엔드 프로세스 종료
FRONTEND_PIDS=$(lsof -ti :5173 2>/dev/null)
if [ -n "$FRONTEND_PIDS" ]; then
  echo "[Frontend] 기존 프로세스 종료 (PID: $FRONTEND_PIDS)"
  kill $FRONTEND_PIDS 2>/dev/null
  sleep 1
fi

# 백엔드 서버 시작
echo "[Backend] 서버 시작 (port 8000)"
source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR/backend"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# 프론트엔드 서버 시작
echo "[Frontend] 서버 시작 (port 5173)"
cd "$PROJECT_DIR/frontend"
npm run dev &

wait
