"""
SPLADE Sparse Encoder for Qdrant Hybrid Search

SPLADE (Sparse Lexical and Dense) 모델을 사용하여
의미 기반 sparse 벡터를 생성합니다.

사용 모델: yjoonjang/splade-ko-v1 (한국어 최적화)
"""

import os
from typing import List, Tuple, Optional
from loguru import logger

import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer


class SPLADEEncoder:
    """
    SPLADE Sparse Encoder for Qdrant Hybrid Search

    Qdrant의 sparse vector와 함께 사용하여
    dense + sparse 하이브리드 검색을 구현합니다.
    """

    # 싱글톤 인스턴스
    _instance: Optional["SPLADEEncoder"] = None

    def __init__(
        self,
        model_name: str = "yjoonjang/splade-ko-v1",
        device: Optional[str] = None,
        max_length: int = 512
    ):
        """
        Args:
            model_name: SPLADE 모델 이름 (기본: 한국어 최적화 모델)
            device: 사용할 디바이스 (None이면 자동 선택)
            max_length: 최대 토큰 길이
        """
        self.model_name = model_name
        self.max_length = max_length

        # 디바이스 설정
        if device is None:
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
        else:
            self.device = device

        logger.info(f"Loading SPLADE model: {model_name}")
        logger.info(f"Device: {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForMaskedLM.from_pretrained(model_name)
        self.model.eval()
        self.model.to(self.device)

        # 어휘 크기
        self.vocab_size = self.tokenizer.vocab_size
        logger.info(f"SPLADE loaded. Vocab size: {self.vocab_size}")

    @classmethod
    def get_instance(
        cls,
        model_name: str = "yjoonjang/splade-ko-v1",
        device: Optional[str] = None
    ) -> "SPLADEEncoder":
        """
        싱글톤 인스턴스 반환 (모델 로딩 시간 절약)
        """
        if cls._instance is None:
            cls._instance = cls(model_name=model_name, device=device)
        return cls._instance

    def encode(self, text: str) -> Tuple[List[int], List[float]]:
        """
        단일 텍스트를 SPLADE sparse 벡터로 인코딩

        Args:
            text: 입력 텍스트

        Returns:
            (indices, values): sparse 벡터의 인덱스와 값
        """
        with torch.no_grad():
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=self.max_length,
                truncation=True,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            output = self.model(**inputs)
            logits = output.logits
            attention_mask = inputs["attention_mask"]

            # SPLADE 스파스 벡터 계산
            # max pooling over sequence + ReLU + log
            sparse_vec = torch.max(
                torch.log(1 + torch.relu(logits)) * attention_mask.unsqueeze(-1),
                dim=1
            )[0].squeeze()

            # 0이 아닌 값만 추출
            indices = sparse_vec.nonzero().squeeze(-1).cpu().tolist()
            values = sparse_vec[indices].cpu().tolist()

            # 단일 값인 경우 리스트로 변환
            if isinstance(indices, int):
                indices = [indices]
                values = [values]

            return indices, values

    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[Tuple[List[int], List[float]]]:
        """
        배치 텍스트를 SPLADE sparse 벡터로 인코딩

        Args:
            texts: 입력 텍스트 리스트
            batch_size: 배치 크기

        Returns:
            [(indices, values), ...] 리스트
        """
        results = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            with torch.no_grad():
                inputs = self.tokenizer(
                    batch_texts,
                    return_tensors="pt",
                    max_length=self.max_length,
                    truncation=True,
                    padding=True
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                output = self.model(**inputs)
                logits = output.logits
                attention_mask = inputs["attention_mask"]

                # 배치 처리
                sparse_vecs = torch.max(
                    torch.log(1 + torch.relu(logits)) * attention_mask.unsqueeze(-1),
                    dim=1
                )[0]

                for sparse_vec in sparse_vecs:
                    indices = sparse_vec.nonzero().squeeze(-1).cpu().tolist()
                    values = sparse_vec[indices].cpu().tolist()

                    if isinstance(indices, int):
                        indices = [indices]
                        values = [values]

                    results.append((indices, values))

        return results
