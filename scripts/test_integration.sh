#!/bin/bash

echo "======================================"
echo "LawLaw Monorepo Integration Test"
echo "======================================"

# PYTHONPATH 설정
export PYTHONPATH=$(pwd):$PYTHONPATH

# 1. libs/rag_core import 테스트
echo -e "\n[1/5] Testing libs/rag_core imports..."
python3 << 'PYTHON_EOF'
from libs.rag_core import (
    KoreanLegalEmbedder,
    ChromaVectorDB,
    create_llm_client,
    HybridRetriever
)
print("✅ libs/rag_core imports successful")
PYTHON_EOF

if [ $? -ne 0 ]; then
    echo "❌ libs/rag_core import test failed"
    exit 1
fi

# 2. apps/backend import 테스트
echo -e "\n[2/5] Testing apps/backend imports..."
python3 << 'PYTHON_EOF'
from apps.backend.models.user import User
from apps.backend.services.file_parser import FileParser
print("✅ apps/backend imports successful")
PYTHON_EOF

if [ $? -ne 0 ]; then
    echo "❌ apps/backend import test failed"
    exit 1
fi

# 3. Backend 실행 가능 여부 확인
echo -e "\n[3/5] Checking backend startup..."
cd apps/backend
python main.py > /tmp/backend_test.log 2>&1 &
BACKEND_PID=$!
sleep 5

if kill -0 $BACKEND_PID 2>/dev/null; then
    echo "✅ Backend starts successfully"
    kill $BACKEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
else
    echo "❌ Backend failed to start"
    echo "Backend log:"
    tail -20 /tmp/backend_test.log
    exit 1
fi

cd ../..

# 4. Frontend 의존성 확인
echo -e "\n[4/5] Checking frontend dependencies..."
cd apps/web-frontend
if [ -d "node_modules" ]; then
    echo "✅ Frontend node_modules exist"
else
    echo "⚠️  Frontend dependencies not installed, running npm install..."
    npm install
fi
cd ../..

# 5. 디렉토리 구조 검증
echo -e "\n[5/5] Verifying directory structure..."
REQUIRED_DIRS=(
    "apps/backend"
    "apps/web-frontend"
    "libs/rag_core"
    "libs/domain_model"
    "data"
    "configs"
    "docs"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir"
    else
        echo "  ❌ $dir (missing)"
        exit 1
    fi
done

echo -e "\n======================================"
echo "✅ All integration tests passed!"
echo "======================================"
