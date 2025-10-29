"""
Index Cache Manager for RAG Pipeline
인덱스 캐시를 관리하여 실험 간 재사용을 가능하게 함
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import shutil


class IndexCacheManager:
    """인덱스 캐시 관리자"""

    def __init__(self, cache_dir: str = "experiments/indexed_data"):
        """
        Initialize cache manager.

        Args:
            cache_dir: 캐시 저장 디렉토리
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()

    def generate_cache_key(self, config: Dict[str, Any]) -> str:
        """
        Config에서 캐시 키 생성.
        청킹, 임베딩, Vector DB 설정을 조합

        Args:
            config: 실험 설정

        Returns:
            캐시 키 문자열
        """
        # 캐시에 영향을 주는 핵심 설정들
        cache_components = []

        # 청킹 설정
        chunking = config.get('chunking', {})
        strategy = chunking.get('strategy', 'fixed')
        chunk_size = chunking.get('chunk_size', 512)
        cache_components.append(f"{strategy}_{chunk_size}")

        # 임베딩 설정
        embedding = config.get('embedding', {})
        emb_type = embedding.get('type', 'huggingface')
        emb_model = embedding.get('model', 'bge-m3').replace('/', '_')
        cache_components.append(f"{emb_type}_{emb_model}")

        # Vector Store 설정
        vector_store = config.get('vector_store', {})
        vs_type = vector_store.get('type', 'faiss')
        vs_index = vector_store.get('index_type', 'flat')
        cache_components.append(f"{vs_type}_{vs_index}")

        # 데이터 버전 (선택)
        data_version = config.get('data', {}).get('version', 'v1')
        cache_components.append(data_version)

        return "_".join(cache_components)

    def get_cache_path(self, cache_key: str) -> Path:
        """
        캐시 키에 해당하는 디렉토리 경로 반환.

        Args:
            cache_key: 캐시 키

        Returns:
            캐시 디렉토리 경로
        """
        return self.cache_dir / cache_key

    def exists(self, cache_key: str) -> bool:
        """
        캐시 존재 여부 확인.

        Args:
            cache_key: 캐시 키

        Returns:
            캐시 존재 여부
        """
        cache_path = self.get_cache_path(cache_key)
        return cache_path.exists() and (cache_path / "index.faiss").exists()

    def save_cache(self, cache_key: str, source_path: Path, config: Dict[str, Any], stats: Dict[str, Any] = None):
        """
        인덱스를 캐시에 저장.

        Args:
            cache_key: 캐시 키
            source_path: 원본 인덱스 경로
            config: 실험 설정
            stats: 인덱싱 통계
        """
        cache_path = self.get_cache_path(cache_key)

        # 디렉토리 생성
        cache_path.mkdir(parents=True, exist_ok=True)

        # 인덱스 파일 복사
        if source_path.exists():
            # FAISS 인덱스 복사
            if (source_path / "index.faiss").exists():
                shutil.copy2(source_path / "index.faiss", cache_path / "index.faiss")

            # 메타데이터 복사
            if (source_path / "data.json").exists():
                shutil.copy2(source_path / "data.json", cache_path / "data.json")

            # Chroma DB 디렉토리 복사
            if (source_path / "chroma_db").exists():
                shutil.copytree(source_path / "chroma_db", cache_path / "chroma_db", dirs_exist_ok=True)

        # 캐시 메타데이터 저장
        cache_info = {
            'cache_key': cache_key,
            'created_at': datetime.now().isoformat(),
            'config': config,
            'stats': stats or {},
            'path': str(cache_path)
        }

        # 설정 파일 저장
        with open(cache_path / "cache_config.json", 'w', encoding='utf-8') as f:
            json.dump(cache_info, f, ensure_ascii=False, indent=2)

        # 전체 메타데이터 업데이트
        self.metadata[cache_key] = cache_info
        self._save_metadata()

        print(f"✅ Cache saved: {cache_key}")

    def load_cache(self, cache_key: str, target_path: Path) -> bool:
        """
        캐시에서 인덱스 로드.

        Args:
            cache_key: 캐시 키
            target_path: 대상 경로

        Returns:
            로드 성공 여부
        """
        if not self.exists(cache_key):
            print(f"⚠️ Cache not found: {cache_key}")
            return False

        cache_path = self.get_cache_path(cache_key)

        # 대상 디렉토리 생성
        target_path.mkdir(parents=True, exist_ok=True)

        # 파일 복사
        try:
            # FAISS 인덱스
            if (cache_path / "index.faiss").exists():
                shutil.copy2(cache_path / "index.faiss", target_path / "index.faiss")

            # 메타데이터
            if (cache_path / "data.json").exists():
                shutil.copy2(cache_path / "data.json", target_path / "data.json")

            # Chroma DB
            if (cache_path / "chroma_db").exists():
                shutil.copytree(cache_path / "chroma_db", target_path / "chroma_db", dirs_exist_ok=True)

            print(f"✅ Cache loaded: {cache_key}")
            return True

        except Exception as e:
            print(f"❌ Failed to load cache: {e}")
            return False

    def list_caches(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 캐시 목록 반환.

        Returns:
            캐시 정보 리스트
        """
        caches = []

        for cache_dir in self.cache_dir.iterdir():
            if cache_dir.is_dir() and cache_dir.name != "cache_metadata.json":
                config_file = cache_dir / "cache_config.json"
                if config_file.exists():
                    with open(config_file, 'r', encoding='utf-8') as f:
                        cache_info = json.load(f)
                        caches.append(cache_info)

        # 생성 시간 순으로 정렬
        caches.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return caches

    def delete_cache(self, cache_key: str) -> bool:
        """
        캐시 삭제.

        Args:
            cache_key: 캐시 키

        Returns:
            삭제 성공 여부
        """
        cache_path = self.get_cache_path(cache_key)

        if cache_path.exists():
            shutil.rmtree(cache_path)

            # 메타데이터에서 제거
            if cache_key in self.metadata:
                del self.metadata[cache_key]
                self._save_metadata()

            print(f"✅ Cache deleted: {cache_key}")
            return True

        return False

    def get_cache_info(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        캐시 정보 조회.

        Args:
            cache_key: 캐시 키

        Returns:
            캐시 정보 딕셔너리
        """
        cache_path = self.get_cache_path(cache_key)
        config_file = cache_path / "cache_config.json"

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        return None

    def _load_metadata(self) -> Dict[str, Any]:
        """전체 메타데이터 로드."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_metadata(self):
        """전체 메타데이터 저장."""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def suggest_cache_key(self, config: Dict[str, Any]) -> Optional[str]:
        """
        현재 설정과 유사한 캐시 키 제안.

        Args:
            config: 실험 설정

        Returns:
            제안 캐시 키 또는 None
        """
        # 검색/생성만 다른 경우 기존 캐시 제안
        target_chunking = config.get('chunking', {})
        target_embedding = config.get('embedding', {})
        target_vector = config.get('vector_store', {})

        for cache_key, cache_info in self.metadata.items():
            cached_config = cache_info.get('config', {})

            # 청킹, 임베딩, Vector DB가 같으면 제안
            if (cached_config.get('chunking') == target_chunking and
                cached_config.get('embedding') == target_embedding and
                cached_config.get('vector_store') == target_vector):
                return cache_key

        return None