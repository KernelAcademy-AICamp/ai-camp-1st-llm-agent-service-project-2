#!/bin/bash

set -e

echo "==========================================="
echo "Django Integration Test"
echo "==========================================="

# 1. AI Service 헬스체크
echo ""
echo "[1/5] Testing AI Service..."
AI_STATUS=$(curl -s http://localhost:8001/health | python -m json.tool | grep -o '"status": "[^"]*"' | cut -d'"' -f4)
echo "AI Service: $AI_STATUS"

if [ "$AI_STATUS" != "healthy" ]; then
    echo "❌ AI Service is not healthy!"
    exit 1
fi

# 2. Django 헬스체크
echo ""
echo "[2/5] Testing Django Backend..."
curl -s http://localhost:8000/api/v1/ai/health | python -m json.tool

# 3. 회원가입
echo ""
echo "[3/5] Testing User Signup..."
SIGNUP_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-django@example.com",
    "password": "testpass123",
    "username": "djangotest",
    "full_name": "Django 테스트"
  }')
echo "$SIGNUP_RESPONSE" | python -m json.tool

# 4. 로그인 및 토큰 획득
echo ""
echo "[4/5] Testing Login & JWT..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-django@example.com",
    "password": "testpass123"
  }' | python -c "import sys, json; print(json.load(sys.stdin)['access'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get JWT token!"
    exit 1
fi

echo "Token: ${TOKEN:0:50}..."

# 5. RAG 챗봇 테스트 (Django → AI Service)
echo ""
echo "[5/5] Testing RAG Chat (Django → AI Service)..."
ANSWER=$(curl -s -X POST http://localhost:8000/api/v1/ai/chat/rag \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "음주운전 처벌 기준",
    "top_k": 2,
    "include_sources": false
  }' | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('answer', 'NO ANSWER'))" 2>/dev/null)

if [ -z "$ANSWER" ] || [ "$ANSWER" == "NO ANSWER" ]; then
    echo "❌ RAG chat failed!"
    exit 1
fi

echo "Answer: ${ANSWER:0:100}..."

echo ""
echo "==========================================="
echo "✅ All Django integration tests passed!"
echo "==========================================="
