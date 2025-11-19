"""
BM25 기반 키워드 검색 인덱스

학습 목적:
- BM25 알고리즘: TF-IDF의 개선 버전, 문서 길이 정규화 포함
- Sparse Retrieval: 키워드 기반 검색 (조항, 판례 번호 등에 강함)
- Hybrid Search의 핵심 컴포넌트
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import pickle
from loguru import logger
from rank_bm25 import BM25Okapi
import re


class BM25Index:
    """BM25 알고리즘 기반 키워드 검색 인덱스"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: BM25 파라미터 (term frequency saturation, 기본 1.5)
            b: BM25 파라미터 (length normalization, 기본 0.75)

        학습 노트:
            - k1: 높을수록 term frequency 영향 증가 (1.2~2.0 범위)
            - b: 높을수록 문서 길이 정규화 강화 (0~1 범위)
            - 기본값(1.5, 0.75)은 대부분의 경우에 잘 작동
        """
        self.k1 = k1
        self.b = b
        self.bm25: Optional[BM25Okapi] = None

        # 문서 저장 (검색 결과 반환용)
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []

        logger.info(f"Initialized BM25Index (k1={k1}, b={b})")

    def tokenize(self, text: str) -> List[str]:
        """
        텍스트 토큰화

        학습 목적: 한국어 토큰화 전략
            - 간단한 방법: 띄어쓰기 기반 split
            - 고급 방법: Mecab, KoNLPy 등 형태소 분석기 사용
            - 법률 문서: 조항 번호, 판례 번호 등 패턴 보존이 중요

        현재 구현:
            - 띄어쓰기 기반 토큰화
            - 특수문자 보존 (제329조, 2023도1234 등)
            - 소문자 변환 (대소문자 무시)
        """
        # 공백 기준 split
        tokens = text.split()

        # 소문자 변환 (영문의 경우)
        tokens = [token.lower() for token in tokens]

        # 빈 토큰 제거
        tokens = [token for token in tokens if token.strip()]

        return tokens

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        문서 추가 및 인덱싱

        Args:
            texts: 문서 텍스트 리스트
            metadatas: 메타데이터 리스트 (선택)
        """
        if not texts:
            logger.warning("No documents to add")
            return

        # 기본 메타데이터 생성
        if metadatas is None:
            metadatas = [{} for _ in texts]

        if len(texts) != len(metadatas):
            raise ValueError(f"texts ({len(texts)}) and metadatas ({len(metadatas)}) length mismatch")

        # 문서 저장
        self.documents.extend(texts)
        self.metadatas.extend(metadatas)

        # 토큰화
        new_tokenized = [self.tokenize(text) for text in texts]
        self.tokenized_corpus.extend(new_tokenized)

        # BM25 인덱스 재구축
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        logger.info(f"Added {len(texts)} documents to BM25 index. Total: {len(self.documents)}")

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        BM25 기반 문서 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 수
            score_threshold: 최소 점수 (이 값 미만은 제외)

        Returns:
            검색 결과 리스트 (score, text, metadata 포함)

        학습 노트:
            - BM25 점수는 0 이상의 실수 (높을수록 관련성 높음)
            - Cosine similarity와 달리 절대값이 아닌 상대적 순위가 중요
            - "제329조" 같은 정확한 키워드는 높은 점수 획득
        """
        if self.bm25 is None:
            logger.warning("BM25 index not initialized. Add documents first.")
            return []

        # 쿼리 토큰화
        tokenized_query = self.tokenize(query)

        if not tokenized_query:
            logger.warning("Empty query after tokenization")
            return []

        # BM25 검색
        scores = self.bm25.get_scores(tokenized_query)

        # 점수와 인덱스 페어링 후 정렬
        doc_scores = list(enumerate(scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        # Top-K 결과 생성
        results = []
        for idx, score in doc_scores[:top_k]:
            # 점수 임계값 체크
            if score < score_threshold:
                continue

            results.append({
                'id': f"bm25_{idx}",
                'text': self.documents[idx],
                'metadata': self.metadatas[idx],
                'score': float(score),
                'search_type': 'bm25'
            })

        logger.info(f"BM25 search: '{query}' -> {len(results)} results")
        return results

    def get_count(self) -> int:
        """인덱싱된 문서 개수 반환"""
        return len(self.documents)

    def save(self, path: str) -> None:
        """
        인덱스 저장

        Args:
            path: 저장 디렉토리 경로
        """
        save_path = Path(path)
        save_path.mkdir(parents=True, exist_ok=True)

        # BM25 모델 저장 (직렬화)
        with open(save_path / "bm25_model.pkl", "wb") as f:
            pickle.dump(self.bm25, f)

        # 문서 및 메타데이터 저장
        with open(save_path / "documents.pkl", "wb") as f:
            pickle.dump(self.documents, f)

        with open(save_path / "metadatas.pkl", "wb") as f:
            pickle.dump(self.metadatas, f)

        with open(save_path / "tokenized_corpus.pkl", "wb") as f:
            pickle.dump(self.tokenized_corpus, f)

        # 설정 저장
        config = {'k1': self.k1, 'b': self.b}
        with open(save_path / "config.pkl", "wb") as f:
            pickle.dump(config, f)

        logger.info(f"Saved BM25 index to {save_path} ({len(self.documents)} documents)")

    def load(self, path: str) -> None:
        """
        인덱스 로드

        Args:
            path: 로드할 디렉토리 경로
        """
        load_path = Path(path)

        if not load_path.exists():
            raise FileNotFoundError(f"BM25 index not found at {load_path}")

        # BM25 모델 로드
        with open(load_path / "bm25_model.pkl", "rb") as f:
            self.bm25 = pickle.load(f)

        # 문서 및 메타데이터 로드
        with open(load_path / "documents.pkl", "rb") as f:
            self.documents = pickle.load(f)

        with open(load_path / "metadatas.pkl", "rb") as f:
            self.metadatas = pickle.load(f)

        with open(load_path / "tokenized_corpus.pkl", "rb") as f:
            self.tokenized_corpus = pickle.load(f)

        # 설정 로드
        with open(load_path / "config.pkl", "rb") as f:
            config = pickle.load(f)
            self.k1 = config['k1']
            self.b = config['b']

        logger.info(f"Loaded BM25 index from {load_path} ({len(self.documents)} documents)")

    def get_top_keywords(self, query: str, top_n: int = 5) -> List[tuple]:
        """
        쿼리에서 중요한 키워드 추출

        Args:
            query: 검색 쿼리
            top_n: 반환할 키워드 수

        Returns:
            (키워드, IDF 점수) 튜플 리스트

        학습 목적: BM25의 IDF(Inverse Document Frequency) 활용
        """
        if self.bm25 is None:
            return []

        tokenized_query = self.tokenize(query)

        # IDF 점수 계산
        keyword_scores = []
        for token in tokenized_query:
            if token in self.bm25.idf:
                keyword_scores.append((token, self.bm25.idf[token]))

        # IDF 점수로 정렬
        keyword_scores.sort(key=lambda x: x[1], reverse=True)

        return keyword_scores[:top_n]

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        쿼리 분석 (디버깅 및 학습용)

        Returns:
            쿼리 토큰, 키워드, 통계 등
        """
        tokens = self.tokenize(query)
        keywords = self.get_top_keywords(query)

        # 조항/판례 번호 패턴 감지
        statute_pattern = re.compile(r'제\d+조')
        case_pattern = re.compile(r'\d{4}도\d+')

        has_statute = bool(statute_pattern.search(query))
        has_case_number = bool(case_pattern.search(query))

        return {
            'query': query,
            'tokens': tokens,
            'token_count': len(tokens),
            'top_keywords': keywords,
            'has_statute_ref': has_statute,
            'has_case_number': has_case_number,
            'total_docs': len(self.documents)
        }
