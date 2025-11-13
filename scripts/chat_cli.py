"""
형사법 RAG 챗봇 CLI

실행 방법:
    python scripts/chat_cli.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from loguru import logger
from configs.config import config
from backend.core.embeddings.embedder import KoreanLegalEmbedder
from backend.core.embeddings.vectordb import create_vector_db
from backend.core.retrieval.retriever import LegalDocumentRetriever
from backend.core.llm.llm_client import create_llm_client
from backend.core.llm.rag_chatbot import RAGChatbot


def print_banner():
    """배너 출력"""
    banner = """
╔═══════════════════════════════════════════════════╗
║          ⚖️  형사법 AI 상담사 CLI  ⚖️           ║
║                                                   ║
║  형사법 판례, 법령, 해석례 기반 AI 챗봇         ║
╚═══════════════════════════════════════════════════╝
    """
    print(banner)
    print("\n명령어:")
    print("  - 'quit', 'exit', 'q': 종료")
    print("  - 'clear', 'c': 대화 히스토리 초기화")
    print("  - 'help', 'h': 도움말")
    print("\n")


def print_help():
    """도움말 출력"""
    help_text = """
사용 방법:
  질문을 입력하면 AI가 관련 판례/법령을 검색하여 답변합니다.

예시 질문:
  - 절도죄의 구성요건은 무엇인가요?
  - 정당방위가 성립하는 요건은?
  - 업무상 횡령죄와 배임죄의 차이는?

주의사항:
  - 이 서비스는 법률 정보 제공 목적입니다
  - 실제 법률 자문이 아닙니다
  - 중요한 사안은 변호사와 상담하세요
    """
    print(help_text)


def initialize_chatbot(args):
    """챗봇 초기화"""
    logger.info("Initializing chatbot...")

    # Load embedder
    embedder = KoreanLegalEmbedder(
        model_name=config.embedding.model_name,
        device=config.embedding.device
    )

    # Load vector database
    if args.db_type == "chroma":
        vectordb = create_vector_db(
            "chroma",
            persist_directory=config.vectordb.chroma_persist_dir,
            collection_name=config.vectordb.collection_name
        )
    else:
        vectordb = create_vector_db(
            "faiss",
            index_path=config.vectordb.faiss_index_path,
            dimension=embedder.get_embedding_dimension()
        )
        vectordb.load()

    # Create retriever
    retriever = LegalDocumentRetriever(
        vectordb=vectordb,
        embedder=embedder,
        top_k=args.top_k
    )

    # Create LLM client
    if args.llm_provider == "openai":
        llm_client = create_llm_client(
            provider="openai",
            api_key=config.llm.openai_api_key,
            model=config.llm.model_name,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens
        )
    else:
        llm_client = create_llm_client(
            provider="anthropic",
            api_key=config.llm.anthropic_api_key,
            model=config.llm.model_name,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens
        )

    # Create chatbot
    chatbot = RAGChatbot(
        retriever=retriever,
        llm_client=llm_client
    )

    logger.info("Chatbot initialized successfully!")
    return chatbot


def main():
    parser = argparse.ArgumentParser(description="Criminal Law RAG Chatbot CLI")
    parser.add_argument("--db_type", type=str, default="chroma", choices=["chroma", "faiss"])
    parser.add_argument("--llm_provider", type=str, default="openai", choices=["openai", "anthropic"])
    parser.add_argument("--top_k", type=int, default=5, help="Number of documents to retrieve")
    parser.add_argument("--show_sources", action="store_true", help="Show source documents")

    args = parser.parse_args()

    print_banner()

    # Initialize chatbot
    try:
        chatbot = initialize_chatbot(args)
    except Exception as e:
        print(f"❌ 챗봇 초기화 실패: {e}")
        print("\n벡터 데이터베이스가 구축되었는지 확인하세요:")
        print("  python scripts/build_vectordb.py")
        return

    print("✅ 챗봇이 준비되었습니다! 질문을 입력하세요.\n")

    # Main loop
    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 종료합니다. 안녕히 가세요!")
                break

            elif user_input.lower() in ['clear', 'c']:
                chatbot.clear_history()
                print("\n🔄 대화 히스토리가 초기화되었습니다.")
                continue

            elif user_input.lower() in ['help', 'h']:
                print_help()
                continue

            # Generate response
            print("\n🤖 AI: ", end="", flush=True)

            response = chatbot.chat_with_history(user_input, top_k=args.top_k)
            answer = response['answer']
            sources = response['sources']

            print(answer)

            # Show sources if requested
            if args.show_sources and sources:
                print("\n📚 참고 문서:")
                for i, source in enumerate(sources[:3]):  # Show top 3
                    source_type = source.get('metadata', {}).get('source_type', 'unknown')
                    source_names = {
                        'court_decision': '판례',
                        'statute': '법령',
                        'interpretation': '해석례',
                        'constitutional': '헌법재판소 결정례'
                    }
                    source_name = source_names.get(source_type, source_type)
                    score = source.get('score', 0)

                    print(f"\n  [{i+1}] {source_name} (관련도: {score:.3f})")
                    print(f"  {source['text'][:200]}...")

        except KeyboardInterrupt:
            print("\n\n👋 종료합니다. 안녕히 가세요!")
            break

        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            logger.error(f"Error: {e}")


if __name__ == "__main__":
    main()
