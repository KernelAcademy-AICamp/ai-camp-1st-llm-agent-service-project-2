#!/usr/bin/env python3
"""
Ollama를 사용한 한국 형사법 AI 테스트 스크립트
"""
import requests
import json

class KosaulLLM:
    def __init__(self, model_name="kosaul-q4"):
        self.model_name = model_name
        self.base_url = "http://localhost:11434"

    def generate(self, prompt, temperature=0.7):
        """Ollama API를 사용하여 응답 생성"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": False
                }
            )

            if response.status_code == 200:
                return response.json()["response"]
            else:
                return f"Error: {response.status_code}"

        except requests.exceptions.ConnectionError:
            return "Ollama가 실행 중이 아닙니다. 'ollama serve'를 먼저 실행하세요."

    def chat(self, message, context=None):
        """대화형 응답 생성"""
        try:
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            messages.append({"role": "user", "content": message})

            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False
                }
            )

            if response.status_code == 200:
                return response.json()["message"]["content"]
            else:
                return f"Error: {response.status_code}"

        except requests.exceptions.ConnectionError:
            return "Ollama가 실행 중이 아닙니다. 'ollama serve'를 먼저 실행하세요."

def main():
    # Kosaul Q4 모델 초기화
    llm = KosaulLLM("kosaul-q4")

    print("🏛️ 한국 형사법 AI 어시스턴트 (Q4_K_M)")
    print("-" * 50)

    # 테스트 질문들
    test_questions = [
        "형법상 정당방위의 성립요건은 무엇인가요?",
        "사기죄와 횡령죄의 차이점을 간단히 설명해주세요.",
        "음주운전의 처벌 기준은 어떻게 되나요?"
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n질문 {i}: {question}")
        print("답변:", llm.generate(question))
        print("-" * 50)

    # 대화형 모드
    print("\n💬 대화 모드 (종료: 'quit' 입력)")
    while True:
        user_input = input("\n질문: ")
        if user_input.lower() in ['quit', 'exit', '종료']:
            break

        response = llm.chat(user_input)
        print("답변:", response)

if __name__ == "__main__":
    main()