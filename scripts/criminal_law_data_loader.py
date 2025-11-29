"""
Criminal Law Data Loader
원천데이터 + 라벨링데이터 통합 로더
Training/Validation split 지원
"""

import os
import json
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm


class CriminalLawDataLoader:
    """형사법 데이터 로더 - 원천데이터 + 라벨링데이터 통합"""

    def __init__(self, base_path: str = None, chunk_size: int = 500):
        """
        Initialize data loader.

        Args:
            base_path: 데이터 기본 경로
            chunk_size: 텍스트 청킹 크기 (기본 500자)
        """
        if base_path is None:
            # 기본 경로 자동 탐지
            project_root = Path(__file__).parent.parent
            # 환경변수로 오버라이드 가능
            import os
            default_path = project_root / "data" / "raw" / "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터" / "3.개방데이터" / "1.데이터"
            base_path = os.getenv("CRIMINAL_LAW_BASE_PATH", str(default_path))

        self.base_path = Path(base_path)
        self.training_path = self.base_path / "Training"
        self.validation_path = self.base_path / "Validation"

        # 경로 설정
        self.source_path = self.training_path / "01.원천데이터"
        self.labeled_path = self.training_path / "02.라벨링데이터"

        # 청킹 설정
        self.chunk_size = chunk_size

        self.stats = {}

        # ⭐ 메타데이터 매핑 로드 (원천데이터에 라벨링 메타데이터 적용용)
        self.metadata_mapping = self._load_metadata_mapping()

    def _load_metadata_mapping(self) -> Dict[str, Dict]:
        """메타데이터 매핑 파일 로드"""
        mapping_path = Path(__file__).parent.parent / "data" / "metadata_mapping.json"

        if mapping_path.exists():
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                print(f"✅ 메타데이터 매핑 로드 완료: {sum(len(v) for v in mapping.values()):,}개")
                return mapping
            except Exception as e:
                print(f"⚠️ 메타데이터 매핑 로드 실패: {e}")
                return {'precedent': {}, 'decision': {}, 'interpretation': {}, 'law': {}}
        else:
            print("⚠️ 메타데이터 매핑 파일 없음. 원천데이터 메타데이터가 제한됩니다.")
            print("   실행: python scripts/build_metadata_mapping.py")
            return {'precedent': {}, 'decision': {}, 'interpretation': {}, 'law': {}}

    def _normalize_id(self, id_value: str, id_type: str) -> str:
        """
        ID 정규화 - 매핑 파일의 ID 형식과 일치시킴

        Args:
            id_value: 원본 ID 값
            id_type: ID 유형 ('law', 'precedent', 'decision', 'interpretation')

        Returns:
            정규화된 ID (법령은 6자리 패딩, 나머지는 그대로)
        """
        if not id_value:
            return id_value

        id_str = str(id_value).strip()

        # 법령 ID는 6자리 패딩 (예: 13988 -> 013988)
        if id_type == 'law':
            return id_str.zfill(6)

        return id_str

    def _get_mapped_metadata(self, id_value: str, id_type: str) -> Dict[str, Any]:
        """
        매핑에서 메타데이터 조회 (ID 정규화 적용)

        Args:
            id_value: 원본 ID
            id_type: 'law', 'precedent', 'decision', 'interpretation'

        Returns:
            매핑된 메타데이터 딕셔너리 (없으면 빈 딕셔너리)
        """
        normalized_id = self._normalize_id(id_value, id_type)
        return self.metadata_mapping.get(id_type, {}).get(normalized_id, {})

    def _chunk_text(self, text: str, max_size: int) -> List[str]:
        """텍스트를 문장 단위로 청킹"""
        sentences = re.split(r'(?<=[.?!])\s+|\n', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current_chunk) + len(sentence) <= max_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text[:max_size]]  # 최소 1개 청크 보장

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

            # 모든 원천데이터는 CSV 파일 (split 정보 전달)
            docs = self._load_source_csv(folder_path, doc_type, max_per_type, split)

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

            docs = self._load_labeled_json(folder_path, doc_type, max_per_type, split)
            all_docs.extend(docs)
            self.stats[f'{split}_labeled_{doc_type}'] = len(docs)

        return all_docs

    def _load_source_csv(self, folder_path: Path, doc_type: str, limit: int = None, split: str = 'training') -> List[Dict[str, Any]]:
        """
        원천데이터 CSV 파일 로드 (법령, 판결문, 결정례, 해석례).

        개선사항:
        - '구분' 컬럼을 활용하여 구조 정보 보존
        - 청킹 없이 원본 그대로 반환 (청킹은 별도 모듈에서 수행)
        - 데이터 타입별 메타데이터 추출
        """
        documents = []
        csv_files = list(folder_path.glob("*.csv"))

        if limit:
            csv_files = csv_files[:limit]

        print(f"📚 {doc_type} 원천 CSV 파일 {len(csv_files)}개 로드 중...")

        for csv_file in tqdm(csv_files, desc=f"{doc_type} 로드"):
            try:
                df = pd.read_csv(csv_file, encoding='utf-8')
                df = df.fillna('')  # NaN 처리

                # 데이터 타입별 처리 (split 정보 전달)
                if doc_type == '법령':
                    docs = self._process_law_csv(df, csv_file, split)
                elif doc_type == '판결문':
                    docs = self._process_precedent_csv(df, csv_file, split)
                elif doc_type == '결정례':
                    docs = self._process_decision_csv(df, csv_file, split)
                elif doc_type == '해석례':
                    docs = self._process_interpretation_csv(df, csv_file, split)
                else:
                    # 기본 처리 (이전 방식)
                    docs = self._process_default_csv(df, csv_file, doc_type, split)

                documents.extend(docs)

            except Exception as e:
                # 조용히 스킵
                continue

        return documents

    def _process_law_csv(self, df: pd.DataFrame, csv_file: Path, split: str = 'training') -> List[Dict[str, Any]]:
        """
        법령 CSV 처리 - 조문 단위로 그룹화 + 매핑 메타데이터 적용

        CSV 구조: 법령일련번호, MST, 구분, 문장번호, 내용
        구분 값: 조문, 항, 호, 목
        """
        documents = []

        # 법령 ID와 MST 추출
        law_id = str(df.iloc[0][df.columns[0]]) if len(df) > 0 else csv_file.stem
        mst = str(df.iloc[0].get('MST', '')) if 'MST' in df.columns and len(df) > 0 else ''

        # ⭐ 매핑에서 메타데이터 가져오기 (ID 정규화 적용)
        mapped_meta = self._get_mapped_metadata(law_id, 'law')
        law_title = mapped_meta.get('law_title', '')

        # 조문 단위로 그룹화
        articles = self._group_by_article(df)

        for article in articles:
            content = article['content']
            article_num = article['article_num']
            article_title = article.get('article_title', '')

            # ⭐ 매핑된 법령명으로 헤더 생성
            if law_title and article_title:
                header = f"[{law_title} {article_num} - {article_title}]\n"
            elif law_title:
                header = f"[{law_title} {article_num}]\n"
            elif article_title:
                header = f"[법령 {article_num} - {article_title}]\n"
            else:
                header = f"[법령 {article_num}]\n"

            documents.append({
                'content': header + content,
                'metadata': {
                    'source': '원천_법령',
                    'doc_id': f"{law_id}_{article_num}",
                    'file': csv_file.name,
                    'type': 'source_법령',
                    'data_source': '원천',
                    'doc_type': '법령',
                    'split': split,
                    # 법령 특화 메타데이터
                    'law_id': law_id,
                    'mst': mst,
                    'article_num': article_num,
                    'article_title': article_title,
                    # ⭐ 매핑에서 가져온 메타데이터
                    'law_title': law_title,
                    'ministry': mapped_meta.get('ministry', ''),
                    # 구조 정보
                    'has_structure': True,
                    'structure_type': 'law_article',
                    'gubun_used': True,
                    'has_mapping': bool(mapped_meta)
                }
            })

        return documents

    def _group_by_article(self, df: pd.DataFrame) -> List[Dict]:
        """
        CSV 데이터를 조문 단위로 그룹화

        Returns:
            [{'article_num': '제1조', 'article_title': '목적', 'content': '...'}, ...]
        """
        articles = []
        current_article = None
        current_content = []

        for _, row in df.iterrows():
            gubun = str(row.get('구분', '')).strip()
            content = str(row.get('내용', '')).strip()

            if not content:
                continue

            # 새 조문 시작 감지
            if gubun == '조문':
                # 이전 조문 저장
                if current_article is not None and current_content:
                    articles.append({
                        'article_num': current_article['num'],
                        'article_title': current_article['title'],
                        'content': '\n'.join(current_content)
                    })

                # 새 조문 시작 - 조문 번호와 제목 추출
                article_match = re.match(r'(제\d+조(?:의\d+)?)\s*(?:\(([^)]+)\))?', content)
                if article_match:
                    current_article = {
                        'num': article_match.group(1),
                        'title': article_match.group(2) or ''
                    }
                else:
                    # 장/절 제목 등
                    current_article = {'num': content[:20], 'title': ''}

                current_content = [content]
            else:
                # 현재 조문에 추가 (항, 호, 목)
                if current_article is not None:
                    current_content.append(content)
                else:
                    # 조문 없이 시작하는 경우 (장/절 제목 등)
                    current_content.append(content)

        # 마지막 조문 저장
        if current_article is not None and current_content:
            articles.append({
                'article_num': current_article['num'],
                'article_title': current_article['title'],
                'content': '\n'.join(current_content)
            })
        elif current_content:  # 조문 없이 전체가 하나인 경우
            articles.append({
                'article_num': '전체',
                'article_title': '',
                'content': '\n'.join(current_content)
            })

        return articles

    def _process_precedent_csv(self, df: pd.DataFrame, csv_file: Path, split: str = 'training') -> List[Dict[str, Any]]:
        """
        판결문 CSV 처리 - 섹션별로 그룹화 + 매핑 메타데이터 적용

        CSV 구조: 판례일련번호, 구분, 문장번호, 내용
        구분 값: 판시사항, 판결요지, 참조조문, 판례내용
        """
        documents = []

        # 판례 ID 추출
        precedent_id = str(df.iloc[0][df.columns[0]]) if len(df) > 0 else csv_file.stem

        # ⭐ 매핑에서 메타데이터 가져오기 (ID 정규화 적용)
        mapped_meta = self._get_mapped_metadata(precedent_id, 'precedent')

        # 섹션별로 그룹화
        sections = {}
        for _, row in df.iterrows():
            gubun = str(row.get('구분', 'other')).strip()
            content = str(row.get('내용', '')).strip()

            if not content:
                continue

            if gubun not in sections:
                sections[gubun] = []
            sections[gubun].append(content)

        # 각 섹션을 문서로 저장
        for section_name, contents in sections.items():
            full_content = '\n'.join(contents)

            # ⭐ 매핑된 메타데이터로 헤더 생성
            case_num = mapped_meta.get('case_num', '')
            case_name = mapped_meta.get('case_name', '')
            if case_num and case_name:
                header = f"[{case_num} {case_name} - {section_name}]\n"
            elif case_num:
                header = f"[{case_num} - {section_name}]\n"
            else:
                header = f"[판결문 - {section_name}]\n"

            documents.append({
                'content': header + full_content,
                'metadata': {
                    'source': '원천_판결문',
                    'doc_id': f"{precedent_id}_{section_name}",
                    'file': csv_file.name,
                    'type': 'source_판결문',
                    'data_source': '원천',
                    'doc_type': '판결문',
                    'split': split,
                    # 판결문 특화 메타데이터
                    'precedent_id': precedent_id,
                    'section': section_name,
                    # ⭐ 매핑에서 가져온 메타데이터
                    'case_name': mapped_meta.get('case_name', ''),
                    'case_num': mapped_meta.get('case_num', ''),
                    'sentence_date': mapped_meta.get('sentence_date', ''),
                    'sentence_year': self._extract_year(mapped_meta.get('sentence_date', '')),
                    'court_name': mapped_meta.get('court_name', ''),
                    'court_code': mapped_meta.get('court_code', ''),
                    'case_type': mapped_meta.get('case_type', ''),
                    # 구조 정보
                    'has_structure': True,
                    'structure_type': 'precedent_section',
                    'gubun_used': True,
                    'has_mapping': bool(mapped_meta)
                }
            })

        return documents

    def _process_decision_csv(self, df: pd.DataFrame, csv_file: Path, split: str = 'training') -> List[Dict[str, Any]]:
        """
        결정례 CSV 처리 - 구분=전문이므로 전체 텍스트로 반환 + 매핑 메타데이터 적용

        CSV 구조: 결정례일련번호, 구분, 문장번호, 내용
        구분 값: 전문 (단일 값)
        """
        documents = []

        # 결정례 ID 추출
        decision_id = str(df.iloc[0][df.columns[0]]) if len(df) > 0 else csv_file.stem

        # ⭐ 매핑에서 메타데이터 가져오기 (ID 정규화 적용)
        mapped_meta = self._get_mapped_metadata(decision_id, 'decision')

        # 전체 내용 연결 (구분=전문이므로)
        full_content = '\n'.join([
            str(row.get('내용', '')).strip()
            for _, row in df.iterrows()
            if str(row.get('내용', '')).strip()
        ])

        if full_content:
            # ⭐ 매핑된 메타데이터로 헤더 생성
            case_num = mapped_meta.get('case_num', '')
            if case_num:
                header = f"[결정례 {case_num}]\n"
            else:
                header = f"[결정례 {decision_id}]\n"

            documents.append({
                'content': header + full_content,
                'metadata': {
                    'source': '원천_결정례',
                    'doc_id': str(decision_id),
                    'file': csv_file.name,
                    'type': 'source_결정례',
                    'data_source': '원천',
                    'doc_type': '결정례',
                    'split': split,
                    # 결정례 특화 메타데이터
                    'decision_id': decision_id,
                    # ⭐ 매핑에서 가져온 메타데이터
                    'case_name': mapped_meta.get('case_name', ''),
                    'case_num': mapped_meta.get('case_num', ''),
                    'final_date': mapped_meta.get('final_date', ''),
                    'final_year': self._extract_year(mapped_meta.get('final_date', '')),
                    'case_code': mapped_meta.get('case_code', ''),
                    'court_code': mapped_meta.get('court_code', ''),
                    # 구조 정보 - 패턴 매칭 필요
                    'has_structure': False,
                    'structure_type': 'decision_full',
                    'needs_pattern_matching': True,
                    'has_mapping': bool(mapped_meta)
                }
            })

        return documents

    def _process_interpretation_csv(self, df: pd.DataFrame, csv_file: Path, split: str = 'training') -> List[Dict[str, Any]]:
        """
        해석례 CSV 처리 - 질의요지/회답/이유 구조 보존 + 매핑 메타데이터 적용

        CSV 구조: 해석례일련번호, 구분, 문장번호, 내용
        구분 값: 질의요지, 회답, 이유
        """
        documents = []

        # 해석례 ID 추출
        interp_id = str(df.iloc[0][df.columns[0]]) if len(df) > 0 else csv_file.stem

        # ⭐ 매핑에서 메타데이터 가져오기 (ID 정규화 적용)
        mapped_meta = self._get_mapped_metadata(interp_id, 'interpretation')

        # 섹션별로 그룹화
        sections = {'질의요지': [], '회답': [], '이유': []}
        for _, row in df.iterrows():
            gubun = str(row.get('구분', '')).strip()
            content = str(row.get('내용', '')).strip()

            if not content:
                continue

            if gubun in sections:
                sections[gubun].append(content)

        # 구조화된 내용 생성
        structured_parts = []
        if sections['질의요지']:
            structured_parts.append(f"[질의요지]\n" + '\n'.join(sections['질의요지']))
        if sections['회답']:
            structured_parts.append(f"[회답]\n" + '\n'.join(sections['회답']))
        if sections['이유']:
            structured_parts.append(f"[이유]\n" + '\n'.join(sections['이유']))

        if structured_parts:
            # ⭐ 매핑된 메타데이터로 헤더 생성
            agenda_num = mapped_meta.get('agenda_num', '')
            if agenda_num:
                header = f"[해석례 {agenda_num}]\n"
            else:
                header = f"[해석례 {interp_id}]\n"

            full_content = header + '\n\n'.join(structured_parts)

            documents.append({
                'content': full_content,
                'metadata': {
                    'source': '원천_해석례',
                    'doc_id': str(interp_id),
                    'file': csv_file.name,
                    'type': 'source_해석례',
                    'data_source': '원천',
                    'doc_type': '해석례',
                    'split': split,
                    # 해석례 특화 메타데이터
                    'interpretation_id': interp_id,
                    'has_query': bool(sections['질의요지']),
                    'has_response': bool(sections['회답']),
                    'has_reason': bool(sections['이유']),
                    # ⭐ 매핑에서 가져온 메타데이터
                    'agenda': mapped_meta.get('agenda', ''),
                    'agenda_num': mapped_meta.get('agenda_num', ''),
                    'interp_date': mapped_meta.get('interp_date', ''),
                    'interp_year': self._extract_year(mapped_meta.get('interp_date', '')),
                    'interp_ministry': mapped_meta.get('interp_ministry', ''),
                    'question_ministry': mapped_meta.get('question_ministry', ''),
                    # 구조 정보
                    'has_structure': True,
                    'structure_type': 'interpretation_qa',
                    'gubun_used': True,
                    'has_mapping': bool(mapped_meta)
                }
            })

        return documents

    def _process_default_csv(self, df: pd.DataFrame, csv_file: Path, doc_type: str, split: str = 'training') -> List[Dict[str, Any]]:
        """기본 CSV 처리 - 이전 방식 (fallback)"""
        documents = []

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

        if full_content:
            documents.append({
                'content': full_content,
                'metadata': {
                    'source': f'원천_{doc_type}',
                    'doc_id': str(doc_id),
                    'file': csv_file.name,
                    'type': f'source_{doc_type}',
                    'data_source': '원천',
                    'doc_type': doc_type,
                    'split': split,  # ✅ split 필드 추가
                    'has_structure': False,
                    'gubun_used': False
                }
            })

        return documents

    def _load_labeled_json(self, folder_path: Path, doc_type: str, limit: int = None, split: str = 'training') -> List[Dict[str, Any]]:
        """
        라벨링 JSON 파일 로드 (QA, SUM) - info 메타데이터 포함

        개선사항:
        - info 필드의 모든 메타데이터 추출
        - 날짜 형식 ISO 변환
        - 연도 숫자 필드 추가 (필터링용)
        - 컨텍스트 헤더 추가
        """
        documents = []
        json_files = list(folder_path.glob("*.json"))

        if limit:
            json_files = json_files[:limit]

        print(f"📚 {doc_type} 라벨링 파일 {len(json_files)}개 로드 중...")

        for json_file in tqdm(json_files, desc=f"{doc_type} 로드"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                info = data.get('info', {})
                label_data = data.get('label', {})

                # ========== info 필드 메타데이터 추출 ==========
                base_metadata = self._extract_info_metadata(info, doc_type, json_file.name)
                base_metadata['split'] = split  # ✅ split 필드 추가

                # label 필드 메타데이터
                if label_data.get('instruction'):
                    base_metadata['instruction'] = label_data['instruction']
                # sentenceType은 info에서 먼저 추출, 없으면 label_data에서 추출
                if 'sentence_type' not in base_metadata and label_data.get('sentenceType'):
                    base_metadata['sentence_type'] = label_data['sentenceType']
                # 단어 수 통계
                if label_data.get('originwordCnt'):
                    try:
                        base_metadata['origin_word_cnt'] = int(label_data['originwordCnt'])
                    except:
                        base_metadata['origin_word_cnt'] = label_data['originwordCnt']
                if label_data.get('labelwordCnt'):
                    try:
                        base_metadata['label_word_cnt'] = int(label_data['labelwordCnt'])
                    except:
                        base_metadata['label_word_cnt'] = label_data['labelwordCnt']

                # ========== 콘텐츠 생성 ==========
                # QA 데이터
                if '_QA' in doc_type:
                    input_text = label_data.get('input', '')
                    output_text = label_data.get('output', '')

                    if input_text and output_text:
                        # 컨텍스트 헤더 생성
                        header = self._create_labeled_header(doc_type, base_metadata)
                        content = f"{header}Q: {input_text}\nA: {output_text}"

                        documents.append({
                            'content': content,
                            'metadata': {
                                **base_metadata,
                                'label_type': 'QA',
                                'input': input_text,
                                'output': output_text,
                            }
                        })

                # SUM 데이터
                elif '_SUM' in doc_type:
                    summary_text = label_data.get('output', '')

                    if summary_text:
                        header = self._create_labeled_header(doc_type, base_metadata)
                        content = f"{header}{summary_text}"

                        documents.append({
                            'content': content,
                            'metadata': {
                                **base_metadata,
                                'label_type': 'SUM',
                            }
                        })

            except Exception as e:
                continue

        return documents

    def _extract_info_metadata(self, info: Dict, doc_type: str, filename: str) -> Dict[str, Any]:
        """
        info 필드에서 메타데이터 추출

        데이터 타입별로 다른 필드 추출:
        - 공통: lawClass, DocuType, smClass, fullText, sentenceType
        - 판결문: precedId, caseName, caseNum, sentenceDate, courtName, courtCode, caseTypeName
        - 결정례: determintId, caseName, caseNum, finalDate, caseCode, courtCode
        - 해석례: interpreId, agenda, agendaNum, interpreDate, interpreMinName, interpreMinCode,
                  questionMinName, questionMinCode
        - 법령: lawId, title, ministry, promulgDate, effectDate, promulgNum
        """
        # ✅ doc_type 정규화: "법령_QA" → base_doc_type="법령", label_type="QA"
        base_doc_type = doc_type
        label_type = None
        if '_QA' in doc_type:
            base_doc_type = doc_type.replace('_QA', '')
            label_type = 'QA'
        elif '_SUM' in doc_type:
            base_doc_type = doc_type.replace('_SUM', '')
            label_type = 'SUM'

        base_metadata = {
            'source': f'라벨링_{doc_type}',
            'file': filename,
            'type': f'labeled_{doc_type}',
            'data_source': '라벨링',
            'doc_type': base_doc_type,  # ✅ 정규화된 doc_type
        }

        if label_type:
            base_metadata['label_type'] = label_type  # ✅ 별도의 label_type 필드

        # 공통 info 필드
        if info.get('lawClass'):
            base_metadata['law_class'] = info['lawClass']
        if info.get('DocuType'):
            base_metadata['docu_type'] = info['DocuType']
        if info.get('smClass'):
            base_metadata['sm_class'] = info['smClass']
        if info.get('fullText'):
            base_metadata['full_text'] = info['fullText']

        # 판결문 관련 필드
        if info.get('precedId'):
            base_metadata['precedent_id'] = str(info['precedId'])
        if info.get('caseName'):
            base_metadata['case_name'] = info['caseName']
        if info.get('caseNum'):
            base_metadata['case_num'] = info['caseNum']
        if info.get('sentenceDate'):
            date_str = self._convert_date_format(info['sentenceDate'])
            base_metadata['sentence_date'] = date_str
            year = self._extract_year(date_str)
            if year:
                base_metadata['sentence_year'] = year
        if info.get('courtName'):
            base_metadata['court_name'] = info['courtName']
        if info.get('courtCode'):
            base_metadata['court_code'] = info['courtCode']
        if info.get('caseTypeName'):
            base_metadata['case_type'] = info['caseTypeName']

        # 결정례 관련 필드
        if info.get('determintId'):
            base_metadata['decision_id'] = str(info['determintId'])
        if info.get('finalDate'):
            date_str = self._convert_date_format(info['finalDate'])
            base_metadata['final_date'] = date_str
            year = self._extract_year(date_str)
            if year:
                base_metadata['final_year'] = year
        if info.get('caseCode'):
            base_metadata['case_code'] = info['caseCode']
        # 결정례에도 caseName, caseNum, courtCode가 있음
        # (판결문과 동일한 필드명이지만 결정례에서도 별도로 확인)

        # sentenceType은 info 필드에도 존재 (모든 데이터 타입 공통)
        if info.get('sentenceType'):
            base_metadata['sentence_type'] = info['sentenceType']

        # 해석례 관련 필드
        if info.get('interpreId'):
            base_metadata['interpretation_id'] = str(info['interpreId'])
        if info.get('agenda'):
            base_metadata['agenda'] = info['agenda']
        if info.get('agendaNum'):
            base_metadata['agenda_num'] = info['agendaNum']
        if info.get('interpreDate'):
            date_str = self._convert_date_format(info['interpreDate'])
            base_metadata['interp_date'] = date_str
            year = self._extract_year(date_str)
            if year:
                base_metadata['interp_year'] = year
        if info.get('interpreMinName'):
            base_metadata['interp_ministry'] = info['interpreMinName']
        if info.get('interpreMinCode'):
            base_metadata['interp_min_code'] = info['interpreMinCode']
        if info.get('questionMinName'):
            base_metadata['question_ministry'] = info['questionMinName']
        if info.get('questionMinCode'):
            base_metadata['question_min_code'] = info['questionMinCode']

        # 법령 관련 필드
        if info.get('lawId'):
            base_metadata['law_id'] = str(info['lawId'])
        if info.get('title'):
            base_metadata['title'] = info['title']
        if info.get('ministry'):
            base_metadata['ministry'] = info['ministry']
        if info.get('promulgDate'):
            # YYYYMMDD 형식을 ISO로 변환
            date_str = self._convert_date_format(info['promulgDate'])
            base_metadata['promulg_date'] = date_str
            year = self._extract_year(date_str)
            if year:
                base_metadata['promulg_year'] = year
        if info.get('effectDate'):
            date_str = self._convert_date_format(info['effectDate'])
            base_metadata['effect_date'] = date_str
        if info.get('promulgNum'):
            base_metadata['promulg_num'] = info['promulgNum']

        return base_metadata

    def _convert_date_format(self, date_str: str) -> str:
        """
        날짜 형식 변환

        입력 형식:
        - YYYYMMDD (예: 20080201)
        - YYYY.MM.DD (예: 2008.02.01)
        - YYYY-MM-DD (예: 2008-02-01)

        출력: YYYY-MM-DD (ISO 형식)
        """
        if not date_str:
            return ''

        date_str = str(date_str).strip()

        # YYYYMMDD 형식
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        # YYYY.MM.DD 형식
        if '.' in date_str:
            parts = date_str.replace('.', '-').rstrip('-')
            return parts

        # 이미 ISO 형식
        return date_str

    def _extract_year(self, date_str: str) -> Optional[int]:
        """날짜 문자열에서 연도 추출"""
        if not date_str:
            return None

        try:
            # 처음 4자리를 연도로 추출
            year_str = date_str[:4]
            return int(year_str)
        except:
            return None

    def _create_labeled_header(self, doc_type: str, metadata: Dict[str, Any]) -> str:
        """라벨링 데이터용 컨텍스트 헤더 생성"""

        if '법령' in doc_type:
            title = metadata.get('title', '')
            sm_class = metadata.get('sm_class', '')
            label_type = 'QA' if '_QA' in doc_type else '요약'
            if title:
                if sm_class:
                    return f"[법령 {label_type} - {title} {sm_class}]\n"
                return f"[법령 {label_type} - {title}]\n"

        elif '판결문' in doc_type:
            case_num = metadata.get('case_num', '')
            case_name = metadata.get('case_name', '')
            label_type = 'QA' if '_QA' in doc_type else '요약'
            if case_num:
                if case_name:
                    return f"[판결문 {label_type} - {case_num} {case_name}]\n"
                return f"[판결문 {label_type} - {case_num}]\n"

        elif '결정례' in doc_type:
            case_num = metadata.get('case_num', '')
            decision_id = metadata.get('decision_id', '')
            label_type = 'QA' if '_QA' in doc_type else '요약'
            if case_num:
                return f"[결정례 {label_type} - {case_num}]\n"
            elif decision_id:
                return f"[결정례 {label_type} - {decision_id}]\n"

        elif '해석례' in doc_type:
            agenda_num = metadata.get('agenda_num', '')
            agenda = metadata.get('agenda', '')
            label_type = 'QA' if '_QA' in doc_type else '요약'
            if agenda_num:
                return f"[해석례 {label_type} - {agenda_num}]\n"
            elif agenda:
                return f"[해석례 {label_type} - {agenda[:30]}]\n"

        return ""