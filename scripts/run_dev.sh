#!/bin/bash

# 개발 환경 실행 스크립트

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==================================="
echo "LawLaw Development Environment"
echo "==================================="

# PYTHONPATH 설정
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# .env 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# AI Service 실행 (백그라운드)
echo ""
echo "[1/3] Starting AI Service (port 8001)..."
cd apps/ai-service
python main.py > ../../logs/ai-service.log 2>&1 &
AI_SERVICE_PID=$!
echo "✅ AI Service started (PID: $AI_SERVICE_PID)"

# 5초 대기 (AI Service 초기화)
sleep 5

# Backend 실행 (백그라운드)
cd "$PROJECT_ROOT"
echo ""
echo "[2/3] Starting Backend (port 8000)..."
cd apps/backend
python main.py > ../../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# 5초 대기
sleep 5

# Frontend 실행 (포그라운드)
cd "$PROJECT_ROOT"
echo ""
echo "[3/3] Starting Frontend (port 3000)..."
cd apps/web-frontend
npm start

# Ctrl+C 시 모든 프로세스 종료
trap "kill $AI_SERVICE_PID $BACKEND_PID" EXIT
