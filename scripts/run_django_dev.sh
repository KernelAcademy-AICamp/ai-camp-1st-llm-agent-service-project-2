#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==========================================="
echo "LawLaw Development (Django)"
echo "==========================================="

# PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# .env 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Logs 디렉토리
mkdir -p logs

# AI Service 실행
echo ""
echo "[1/3] Starting AI Service (port 8001)..."
cd apps/ai_service
python main.py > ../../logs/ai_service.log 2>&1 &
AI_PID=$!
echo "✅ AI Service started (PID: $AI_PID)"

sleep 5

# Django Backend 실행
echo ""
echo "[2/3] Starting Django Backend (port 8000)..."
cd "$PROJECT_ROOT/apps/backend_api"
python manage.py runserver 0.0.0.0:8000 > ../../logs/django.log 2>&1 &
DJANGO_PID=$!
echo "✅ Django Backend started (PID: $DJANGO_PID)"

sleep 5

echo ""
echo "==========================================="
echo "✅ All services running!"
echo "==========================================="
echo "AI Service:      http://localhost:8001"
echo "Django Backend:  http://localhost:8000"
echo "Django Admin:    http://localhost:8000/admin"
echo ""
echo "Logs:"
echo "- AI Service:    logs/ai_service.log"
echo "- Django:        logs/django.log"
echo ""
echo "Press Ctrl+C to stop all services"

# Cleanup
trap "echo ''; echo 'Stopping services...'; kill $AI_PID $DJANGO_PID 2>/dev/null; wait; echo 'Done!'" EXIT INT TERM

# Keep script running
wait
