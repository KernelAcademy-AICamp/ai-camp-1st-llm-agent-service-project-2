"""
Colab용 형사법 데이터 임베딩 스크립트
Google Colab Pro+에서 실행하여 ChromaDB에 임베딩

사용법:
1. Colab에 이 스크립트 업로드
2. criminal_law_chunks.jsonl 파일 업로드
3. 셀에서 실행: !python colab_embed_criminal_law.py

필요한 패키지:
!pip install chromadb sentence-transformers
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CriminalLawEmbedder:
    """형사법 데이터 ChromaDB 임베딩"""

    def __init__(
        self,
        jsonl_file: str,
        chroma_db_path: str = "./chroma_db",
        collection_name: str = "criminal_law_docs",
        model_name: str = "jhgan/ko-sroberta-multitask",
        batch_size: int = 100
    ):
        self.jsonl_file = Path(jsonl_file)
        self.chroma_db_path = Path(chroma_db_path)
        self.collection_name = collection_name
        self.batch_size = batch_size

        # 임베딩 모델 로드
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        logger.info("✅ Embedding model loaded")

        # ChromaDB 초기화
        logger.info(f"Initializing ChromaDB at {chroma_db_path}")
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_db_path),
            settings=Settings(anonymized_telemetry=False)
        )

        # 컬렉션 생성 (기존 컬렉션이 있으면 삭제)
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"Deleted existing collection: {self.collection_name}")
        except:
            pass

        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "형사법 판례 및 법령 문서"}
        )
        logger.info(f"✅ Collection created: {self.collection_name}")

    def load_chunks(self) -> List[Dict]:
        """JSONL 파일에서 청크 로드"""
        logger.info(f"Loading chunks from {self.jsonl_file}")

        chunks = []
        with open(self.jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                chunk = json.loads(line)
                chunks.append(chunk)

        logger.info(f"✅ Loaded {len(chunks)} chunks")
        return chunks

    def embed_and_store(self, chunks: List[Dict]):
        """청크를 임베딩하고 ChromaDB에 저장"""
        total_chunks = len(chunks)
        logger.info(f"Starting embedding process for {total_chunks} chunks")

        # 배치 처리
        for i in tqdm(range(0, total_chunks, self.batch_size)):
            batch = chunks[i:i + self.batch_size]

            # 텍스트 추출
            texts = [chunk['text'] for chunk in batch]
            ids = [chunk['id'] for chunk in batch]
            metadatas = [chunk['metadata'] for chunk in batch]

            # 임베딩 생성
            embeddings = self.model.encode(texts, show_progress_bar=False)

            # ChromaDB에 저장
            self.collection.add(
                ids=ids,
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas
            )

            if (i + self.batch_size) % 10000 == 0:
                logger.info(f"Progress: {i + self.batch_size}/{total_chunks} chunks embedded")

        logger.info(f"✅ Embedding complete! Total: {total_chunks} chunks")

    def verify_embedding(self):
        """임베딩 결과 검증"""
        count = self.collection.count()
        logger.info(f"Total documents in ChromaDB: {count}")

        # 샘플 검색 테스트
        test_query = "음주운전 처벌"
        logger.info(f"Test query: {test_query}")

        query_embedding = self.model.encode([test_query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=3
        )

        logger.info("Top 3 results:")
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            logger.info(f"\n{i+1}. {metadata.get('type', 'unknown')} - {metadata.get('source', 'unknown')}")
            logger.info(f"   {doc[:200]}...")

    def run(self):
        """전체 임베딩 프로세스 실행"""
        # 청크 로드
        chunks = self.load_chunks()

        # 임베딩 및 저장
        self.embed_and_store(chunks)

        # 검증
        self.verify_embedding()

        logger.info(f"\n✅ All done! ChromaDB saved at: {self.chroma_db_path}")
        logger.info(f"You can now download the entire '{self.chroma_db_path}' folder")


def main():
    """메인 실행"""
    # 파일 경로 (Colab에 업로드한 파일 경로)
    JSONL_FILE = "criminal_law_chunks.jsonl"

    # ChromaDB 저장 경로
    CHROMA_DB_PATH = "./chroma_criminal_law"

    # 임베더 초기화 및 실행
    embedder = CriminalLawEmbedder(
        jsonl_file=JSONL_FILE,
        chroma_db_path=CHROMA_DB_PATH,
        batch_size=100  # GPU 메모리에 따라 조정 가능
    )

    embedder.run()


if __name__ == "__main__":
    main()
