"""
Criminal Law Data Loader
원천데이터 + 라벨링데이터 통합 로더
Training/Validation split 지원
"""

import os
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm


class CriminalLawDataLoader:
    """형사법 데이터 로더 - 원천데이터 + 라벨링데이터 통합"""

    def __init__(self, base_path: str = None):
        """
        Initialize data loader.

        Args:
            base_path: 데이터 기본 경로
        """
        if base_path is None:
            # 기본 경로 자동 탐지
            project_root = Path(__file__).parent.parent
            base_path = project_root / "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/3.개방데이터/1.데이터"

        self.base_path = Path(base_path)
        self.training_path = self.base_path / "Training"
        self.validation_path = self.base_path / "Validation"

        # 경로 설정
        self.source_path = self.training_path / "01.원천데이터"
        self.labeled_path = self.training_path / "02.라벨링데이터"

        self.stats = {}

    def load_dataset(self,
                    use_source: bool = True,
                    use_labeled: bool = True,
                    source_types: List[str] = None,
                    labeled_types: List[str] = None,
                    max_per_type: int = None,
                    split: str = 'training') -> List[Dict[str, Any]]:
        """
        통합 데이터셋 로드.

        Args:
            use_source: 원천데이터 사용 여부
            use_labeled: 라벨링데이터 사용 여부
            source_types: 원천데이터 타입 ['법령', '판결문', '결정례', '해석례']
            labeled_types: 라벨링데이터 타입 ['법령_QA', '판결문_QA', '판결문_SUM', etc]
            max_per_type: 타입별 최대 문서 수
            split: 데이터 스플릿 'training', 'validation', 'all'

        Returns:
            통합 문서 리스트
        """
        all_documents = []

        # 기본값 설정
        if source_types is None:
            source_types = ['법령', '판결문', '결정례', '해석례']
        if labeled_types is None:
            labeled_types = ['법령_QA', '판결문_QA', '결정례_QA', '해석례_QA']

        # split에 따라 로드할 데이터 결정
        splits_to_load = []
        if split == 'all':
            splits_to_load = ['training', 'validation']
        elif split in ['training', 'validation']:
            splits_to_load = [split]
        else:
            raise ValueError(f"Invalid split: {split}. Must be 'training', 'validation', or 'all'")

        # 각 split에서 데이터 로드
        for current_split in splits_to_load:
            # 원천데이터 로드
            if use_source:
                source_docs = self.load_source_data(source_types, max_per_type, current_split)
                all_documents.extend(source_docs)
                print(f"✓ {current_split} 원천데이터: {len(source_docs)}개 로드")

            # 라벨링데이터 로드
            if use_labeled:
                labeled_docs = self.load_labeled_data(labeled_types, max_per_type, current_split)
                all_documents.extend(labeled_docs)
                print(f"✓ {current_split} 라벨링데이터: {len(labeled_docs)}개 로드")

        # 통계
        print(f"\n📊 전체 로드 통계:")
        print(f"  총 문서 수: {len(all_documents)}")
        for key, value in self.stats.items():
            print(f"  - {key}: {value}")

        return all_documents

    def load_source_data(self,
                        types: List[str] = None,
                        max_per_type: int = None,
                        split: str = 'training') -> List[Dict[str, Any]]:
        """
        원천데이터 로드.

        Args:
            types: 로드할 타입 리스트 ['법령', '판결문', '결정례', '해석례']
            max_per_type: 타입별 최대 문서 수
            split: 'training' or 'validation'

        Returns:
            원천 문서 리스트
        """
        if types is None:
            types = ['법령', '판결문', '결정례', '해석례']

        # split에 따른 경로 설정
        if split == 'training':
            base_path = self.training_path / "01.원천데이터"
            prefix = "TS"
        else:  # validation
            base_path = self.validation_path / "01.원천데이터"
            prefix = "VS"

        all_docs = []

        for doc_type in types:
            folder_name = f"{prefix}_{doc_type}"
            folder_path = base_path / folder_name

            if not folder_path.exists():
                print(f"⚠️ 원천데이터 폴더 없음: {folder_path}")
                continue

            # 모든 원천데이터는 CSV 파일
            docs = self._load_source_csv(folder_path, doc_type, max_per_type)

            all_docs.extend(docs)
            self.stats[f'{split}_source_{doc_type}'] = len(docs)

        return all_docs

    def load_labeled_data(self,
                         types: List[str] = None,
                         max_per_type: int = None,
                         split: str = 'training') -> List[Dict[str, Any]]:
        """
        라벨링데이터 로드.

        Args:
            types: 로드할 타입 리스트 ['법령_QA', '판결문_QA', etc]
            max_per_type: 타입별 최대 문서 수
            split: 'training' or 'validation'

        Returns:
            라벨링 문서 리스트
        """
        if types is None:
            types = ['법령_QA', '판결문_QA', '결정례_QA', '해석례_QA']

        # split에 따른 경로 설정
        if split == 'training':
            base_path = self.training_path / "02.라벨링데이터"
            prefix = "TL"
        else:  # validation
            base_path = self.validation_path / "02.라벨링데이터"
            prefix = "VL"

        all_docs = []

        for doc_type in types:
            folder_name = f"{prefix}_{doc_type}"
            folder_path = base_path / folder_name

            if not folder_path.exists():
                print(f"⚠️ 라벨링데이터 폴더 없음: {folder_path}")
                continue

            docs = self._load_labeled_json(folder_path, doc_type, max_per_type)
            all_docs.extend(docs)
            self.stats[f'{split}_labeled_{doc_type}'] = len(docs)

        return all_docs

    def _load_source_csv(self, folder_path: Path, doc_type: str, limit: int = None) -> List[Dict[str, Any]]:
        """원천데이터 CSV 파일 로드 (법령, 판결문, 결정례, 해석례)."""
        documents = []
        csv_files = list(folder_path.glob("*.csv"))

        if limit:
            csv_files = csv_files[:limit]

        print(f"📚 {doc_type} 원천 CSV 파일 {len(csv_files)}개 로드 중...")

        for csv_file in tqdm(csv_files, desc=f"{doc_type} 로드"):
            try:
                df = pd.read_csv(csv_file, encoding='utf-8')
                df = df.fillna('')  # NaN 처리

                doc_content = []
                doc_id = None

                for _, row in df.iterrows():
                    # 첫 번째 칼럼을 ID로 사용
                    if doc_id is None and len(df.columns) > 0:
                        doc_id = row[df.columns[0]]

                    # '내용' 칼럼이 있으면 사용, 없으면 모든 칼럼 합치기
                    if '내용' in df.columns:
                        content = str(row['내용']).strip()
                    else:
                        content = ' '.join([str(val).strip() for val in row.values if str(val).strip()])

                    if content:
                        doc_content.append(content)

                full_content = "\n".join(doc_content)

                if full_content:  # 내용이 있는 경우만 추가
                    documents.append({
                        'content': full_content,
                        'metadata': {
                            'source': f'원천_{doc_type}',
                            'doc_id': doc_id,
                            'file': csv_file.name,
                            'type': f'source_{doc_type}'
                        }
                    })

            except Exception as e:
                # 조용히 스킵
                continue

        return documents

    def _load_labeled_json(self, folder_path: Path, doc_type: str, limit: int = None) -> List[Dict[str, Any]]:
        """라벨링 JSON 파일 로드 (QA, SUM)."""
        documents = []
        json_files = list(folder_path.glob("*.json"))

        if limit:
            json_files = json_files[:limit]

        print(f"📚 {doc_type} 라벨링 파일 {len(json_files)}개 로드 중...")

        for json_file in tqdm(json_files, desc=f"{doc_type} 로드"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                label_data = data.get('label', {})

                # QA 데이터
                if '_QA' in doc_type:
                    input_text = label_data.get('input', '')
                    output_text = label_data.get('output', '')
                    instruction = label_data.get('instruction', '')

                    if input_text and output_text:
                        # QA 쌍으로 저장
                        content = f"Q: {input_text}\nA: {output_text}"

                        documents.append({
                            'content': content,
                            'metadata': {
                                'source': f'라벨링_{doc_type}',
                                'input': input_text,
                                'output': output_text,
                                'instruction': instruction,
                                'file': json_file.name,
                                'type': f'labeled_{doc_type}'
                            }
                        })

                # SUM 데이터
                elif '_SUM' in doc_type:
                    summary_text = label_data.get('output', '')
                    instruction = label_data.get('instruction', '')

                    if summary_text:
                        documents.append({
                            'content': summary_text,
                            'metadata': {
                                'source': f'라벨링_{doc_type}',
                                'instruction': instruction,
                                'file': json_file.name,
                                'type': f'labeled_{doc_type}'
                            }
                        })

            except Exception as e:
                continue

        return documents
