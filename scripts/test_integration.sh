#!/bin/bash

set -e

echo "======================================="
echo "Integration Test: Backend <-> AI Service"
echo "======================================="

# 1. AI Service 헬스체크
echo ""
echo "[1/4] Testing AI Service..."
curl -s http://localhost:8001/health | jq .

# 2. Backend 헬스체크
echo ""
echo "[2/4] Testing Backend..."
curl -s http://localhost:8000/health | jq .

# 3. Backend Chat 프록시 헬스체크
echo ""
echo "[3/4] Testing Backend Chat Proxy..."
curl -s http://localhost:8000/api/v1/chat/health | jq .

# 4. RAG 챗봇 직접 테스트 (AI Service)
echo ""
echo "[4/4] Testing RAG Chat (AI Service direct)..."
curl -s -X POST http://localhost:8001/v1/chat/rag \
  -H "Content-Type: application/json" \
  -d '{"query": "테스트 질문", "top_k": 1, "include_sources": false}' \
  | jq '.answer'

echo ""
echo "======================================="
echo "✅ All integration tests passed!"
echo "======================================="
