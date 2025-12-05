#!/bin/bash

# PII 마스킹 비교 테스트 실행 스크립트

echo "🔍 PII 마스킹 비교 테스트"
echo "=" 
echo ""

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."

# venv 활성화 확인
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  가상환경이 활성화되지 않았습니다."
    echo "다음 명령어로 활성화하세요:"
    echo "  source venv/bin/activate"
    exit 1
fi

# OpenAI API 키 확인
if [ -z "$OPENAI_API_KEY" ] && [ -z "$LLM_API_KEY" ]; then
    echo "⚠️  OpenAI API 키가 설정되지 않았습니다."
    echo ".env 파일을 확인하세요."
    exit 1
fi

echo "✅ 환경 설정 확인 완료"
echo ""

# Presidio 설치 확인
python -c "import presidio_analyzer" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Presidio가 설치되지 않았습니다."
    echo ""
    echo "설치하시겠습니까? (y/n)"
    read -r answer
    if [ "$answer" = "y" ]; then
        echo "📦 Presidio 설치 중..."
        pip install presidio-analyzer presidio-anonymizer spacy
        python -m spacy download en_core_web_sm
        echo "✅ 설치 완료"
    else
        echo "Presidio 없이 커스텀 방식만 테스트합니다."
    fi
fi

echo ""
echo "🚀 테스트 시작..."
echo ""

# pytest 실행
pytest tests/test_pii_masking_comparison.py -v -s

echo ""
echo "✅ 테스트 완료!"
