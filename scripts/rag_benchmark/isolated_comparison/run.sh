#!/bin/bash
# 격리된 컴포넌트 비교 실행 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

cd "$PROJECT_ROOT"
source venv/bin/activate

echo "========================================"
echo "🔬 격리된 컴포넌트 비교 벤치마크"
echo "========================================"
echo ""

# 1. 데이터 준비
echo "📥 Step 1: 데이터 준비 (샘플링 + 청킹 + 임베딩)"
echo "   샘플 크기: 문서 타입별 300개 (판결문 300 + 결정례 300)"
echo ""

if [ ! -f "$SCRIPT_DIR/data/preparation_summary.json" ]; then
    python "$SCRIPT_DIR/prepare_data.py" --sample-size 300
else
    echo "   ✅ 이미 준비된 데이터 존재. 스킵."
    echo "   (재생성하려면: rm -rf $SCRIPT_DIR/data)"
fi

echo ""

# 2. 비교 실행
echo "📊 Step 2: 격리된 컴포넌트 비교 실행"
echo ""

python "$SCRIPT_DIR/run_isolated_comparison.py"

echo ""
echo "========================================"
echo "✅ 완료!"
echo "========================================"
