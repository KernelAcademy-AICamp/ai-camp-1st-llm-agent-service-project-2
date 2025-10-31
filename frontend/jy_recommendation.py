"""
Legal QnA System - Streamlit Frontend
Criminal law case inquiry system that searches relevant law articles and precedents
"""

import streamlit as st
import sys
from pathlib import Path
import yaml
from datetime import datetime
from dotenv import load_dotenv  # .env 파일 로드용

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file from project root - API 키 등 환경 변수 로드
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    st.warning(f"⚠️ .env file not found at {env_path}")

# Import RAG pipeline modules
from core.rag.pipeline import RAGPipeline
from core.rag.cache_manager import IndexCacheManager  # 캐시 관리자


# Page configuration
st.set_page_config(
    page_title="Legal QnA System",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'rag_pipeline' not in st.session_state:
    st.session_state.rag_pipeline = None
if 'config' not in st.session_state:
    st.session_state.config = None


def load_config(config_path: str) -> dict:
    """Load configuration file"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        st.error(f"Failed to load config: {e}")
        return None


def initialize_rag_pipeline(config: dict):
    """Initialize RAG pipeline"""
    try:
        with st.spinner("Initializing RAG pipeline..."):
            # 캐시 매니저 생성 및 캐시 키 확인
            cache_manager = IndexCacheManager(
                cache_dir=str(project_root / 'experiments' / 'indexed_data')
            )
            cache_key = cache_manager.generate_cache_key(config)

            # 캐시 존재 여부 확인
            if not cache_manager.exists(cache_key):
                st.error(f"❌ Index not found: {cache_key}")
                st.info("""
                Please run indexing first:
                ```bash
                python run.py index --config experiments/configs/members/jy/jy_config_003.yaml
                ```
                """)
                return None

            # 캐시 정보 표시
            cache_info = cache_manager.get_cache_info(cache_key)  # 올바른 메서드 이름
            st.success(f"✅ Cached index found: {cache_key}")
            if cache_info:
                num_chunks = cache_info.get('stats', {}).get('num_chunks', 'N/A')
                created_at = cache_info.get('created_at', 'N/A')
                st.info(f"Chunks: {num_chunks} | Created: {created_at}")
            else:
                st.info("Cache info not available")

            # RAG 파이프라인 초기화
            pipeline = RAGPipeline(config)

            # 캐시된 인덱스 로드
            cache_path = cache_manager.get_cache_path(cache_key)
            pipeline.load_index(str(cache_path))
            st.success("✅ Index loaded successfully!")

        return pipeline
    except Exception as e:
        st.error(f"Failed to initialize RAG pipeline: {e}")
        import traceback
        st.error(traceback.format_exc())  # 디버깅용 상세 에러 표시
        return None


def format_source_documents(documents: list) -> str:
    """Format retrieved documents"""
    if not documents:
        return "No relevant documents found."

    formatted = []
    for idx, doc in enumerate(documents, 1):
        metadata = doc.get('metadata', {})
        content = doc.get('content', '')
        score = doc.get('score', 0.0)

        # Extract document type
        doc_type = metadata.get('type', 'Document')
        doc_id = metadata.get('id', f'doc_{idx}')

        formatted.append(f"""
**[{idx}] {doc_type}** (Similarity: {score:.3f})
- **Document ID**: {doc_id}
- **Content**: {content[:300]}{"..." if len(content) > 300 else ""}
---
""")

    return "\n".join(formatted)


def process_query(pipeline: RAGPipeline, query: str) -> tuple:
    """Process query and return answer with source documents"""
    try:
        with st.spinner("Generating answer..."):
            # RAG 파이프라인의 query() 메서드 사용 (generate 아님)
            result = pipeline.query(query)

            # 반환 형식: {'answer': str, 'sources': list, 'retrieved_documents': list, ...}
            answer = result.get('answer', 'Unable to generate answer.')
            source_docs = result.get('sources', [])  # 'sources' 또는 'retrieved_documents'

            return answer, source_docs
    except Exception as e:
        st.error(f"Query processing failed: {e}")
        return f"Error occurred: {e}", []


def main():
    """Main function"""

    # Header
    st.title("⚖️ Legal QnA System")
    st.markdown("Ask questions about your ongoing case, and we'll find relevant law articles and precedents.")

    # Sidebar - Settings
    with st.sidebar:
        st.header("⚙️ Settings")

        # Select config file
        config_dir = project_root / 'experiments' / 'configs' / 'members' / 'jy'
        if config_dir.exists():
            config_files = list(config_dir.glob("*.yaml"))
            config_names = [f.name for f in config_files]

            if config_names:
                selected_config = st.selectbox(
                    "Select Config File",
                    config_names,
                    index=len(config_names)-1  # Select latest file
                )
                config_path = config_dir / selected_config
            else:
                st.error("No config files found.")
                return
        else:
            st.error(f"Config directory not found: {config_dir}")
            return

        # Load config button
        if st.button("🔄 Initialize System", type="primary"):
            config = load_config(str(config_path))
            if config:
                st.session_state.config = config
                st.session_state.rag_pipeline = initialize_rag_pipeline(config)
                if st.session_state.rag_pipeline:
                    st.success("System initialized successfully!")
                else:
                    st.error("System initialization failed")

        # Display config info
        if st.session_state.config:
            st.divider()
            st.subheader("📋 Current Config")

            gen_config = st.session_state.config.get('generation', {})
            st.markdown(f"""
            - **Model**: {gen_config.get('model_name', 'N/A')}
            - **Temperature**: {gen_config.get('temperature', 'N/A')}
            - **Max Tokens**: {gen_config.get('max_tokens', 'N/A')}
            """)

            retrieval_config = st.session_state.config.get('retrieval', {})
            st.markdown(f"""
            - **Top K Documents**: {retrieval_config.get('top_k', 'N/A')}
            - **Search Strategy**: {retrieval_config.get('strategy', 'N/A')}
            """)

        # Clear chat history button
        st.divider()
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()

    # Main area
    if not st.session_state.rag_pipeline:
        st.info("👈 Please click 'Initialize System' button in the sidebar first.")

        # Show usage examples
        st.subheader("💡 Example Questions")
        st.markdown("""
        **Example queries:**
        - "What are the penalties for DUI causing a traffic accident?"
        - "What are the aggravated punishment criteria for DUI under special criminal law?"
        - "What are the penalties for refusing a breathalyzer test?"
        - "Can a first-time DUI offender receive a suspended sentence?"
        """)
        return

    # Display chat history
    st.subheader("💬 Chat History")
    chat_container = st.container()

    with chat_container:
        for chat in st.session_state.chat_history:
            with st.chat_message("user"):
                st.markdown(chat['query'])

            with st.chat_message("assistant"):
                st.markdown(chat['answer'])

                # Show related documents (collapsible)
                with st.expander("📚 View Related Law Articles and Precedents"):
                    st.markdown(chat['sources'])

    # Query input
    st.divider()
    query = st.chat_input("Enter your question about the case...")

    if query:
        # Display user query
        with st.chat_message("user"):
            st.markdown(query)

        # Generate answer
        answer, source_docs = process_query(
            st.session_state.rag_pipeline,
            query
        )

        # Display answer
        with st.chat_message("assistant"):
            st.markdown(answer)

            # Show related documents
            sources_formatted = format_source_documents(source_docs)
            with st.expander("📚 View Related Law Articles and Precedents"):
                st.markdown(sources_formatted)

        # Add to chat history
        st.session_state.chat_history.append({
            'query': query,
            'answer': answer,
            'sources': sources_formatted,
            'timestamp': datetime.now().isoformat()
        })

        # Refresh screen to update chat history
        st.rerun()


if __name__ == "__main__":
    main()
