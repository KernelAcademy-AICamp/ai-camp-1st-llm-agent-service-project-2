"""
교통사고/도로교통법 관련 데이터 필터링 및 복사
"""

import json
import os
import shutil
from pathlib import Path
from typing import List, Set


# 교통 관련 키워드
TRAFFIC_KEYWORDS = [
    '교통사고', '도로교통법', '교통', '운전', '차량', '자동차',
    '음주운전', '무면허', '신호위반', '속도위반', '중앙선침범',
    '보행자', '횡단보도', '교통법규', '난폭운전', '뺑소니',
    '차선', '도로', '주차', '정차', '면허', '운전면허',
    '특정범죄가중처벌등에관한법률', '교통법', '차량운행',
    '사고운전', '위험운전', '교통사고처리특례법'
]


def check_traffic_related(file_path: str) -> bool:
    """
    파일 내용을 확인하여 교통 관련 여부 판단

    Args:
        file_path: JSON 파일 경로

    Returns:
        교통 관련 여부
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # caseName, input, output 등에서 키워드 검색
        search_fields = []

        # info 섹션
        if 'info' in data:
            if 'caseName' in data['info']:
                search_fields.append(data['info']['caseName'])
            if 'fullText' in data['info'] and isinstance(data['info'].get('fullText'), str):
                search_fields.append(data['info']['fullText'])

        # label 섹션
        if 'label' in data:
            if 'input' in data['label']:
                search_fields.append(data['label']['input'])
            if 'output' in data['label']:
                search_fields.append(data['label']['output'])

        # 전체 텍스트 결합
        full_text = ' '.join(search_fields)

        # 키워드 검색
        for keyword in TRAFFIC_KEYWORDS:
            if keyword in full_text:
                return True

        return False

    except Exception as e:
        print(f"⚠️  파일 읽기 실패: {file_path} - {str(e)}")
        return False


def filter_and_copy_traffic_data(source_dir: str, target_dir: str):
    """
    교통 관련 데이터 필터링 및 복사

    Args:
        source_dir: 소스 디렉토리 (.data)
        target_dir: 타겟 디렉토리 (.data_traffic)
    """
    print("=" * 60)
    print("교통사고/도로교통법 관련 데이터 필터링")
    print("=" * 60)

    source_path = Path(source_dir)
    target_path = Path(target_dir)

    if not source_path.exists():
        print(f"❌ 소스 디렉토리가 없습니다: {source_dir}")
        return

    # 통계
    total_files = 0
    traffic_files = 0
    copied_files = 0

    # JSON 파일 찾기
    print(f"\n소스 디렉토리: {source_dir}")
    print("JSON 파일 검색 중...")

    json_files = list(source_path.rglob("*.json"))
    total_files = len(json_files)

    print(f"총 {total_files:,}개 파일 발견\n")

    # 필터링 및 복사
    print("교통 관련 파일 필터링 중...")

    for i, json_file in enumerate(json_files):
        if (i + 1) % 100 == 0:
            print(f"  진행: {i+1:,}/{total_files:,} ({(i+1)/total_files*100:.1f}%)")

        # 교통 관련 여부 확인
        if check_traffic_related(str(json_file)):
            traffic_files += 1

            # 상대 경로 계산
            rel_path = json_file.relative_to(source_path)
            target_file = target_path / rel_path

            # 타겟 디렉토리 생성
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # 파일 복사
            try:
                shutil.copy2(json_file, target_file)
                copied_files += 1
            except Exception as e:
                print(f"⚠️  복사 실패: {json_file} - {str(e)}")

    # 결과
    print("\n" + "=" * 60)
    print("필터링 완료")
    print("=" * 60)
    print(f"총 파일 수: {total_files:,}")
    print(f"교통 관련 파일: {traffic_files:,} ({traffic_files/total_files*100:.1f}%)")
    print(f"복사 완료: {copied_files:,}")
    print(f"\n타겟 디렉토리: {target_dir}")


def delete_zip_files(directory: str):
    """
    디렉토리 내 모든 .zip 파일 삭제

    Args:
        directory: 검색할 디렉토리
    """
    print("\n" + "=" * 60)
    print("ZIP 파일 삭제")
    print("=" * 60)

    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"❌ 디렉토리가 없습니다: {directory}")
        return

    # ZIP 파일 찾기
    zip_files = list(dir_path.rglob("*.zip"))

    print(f"\n{len(zip_files):,}개 ZIP 파일 발견")

    if len(zip_files) == 0:
        print("삭제할 ZIP 파일이 없습니다.")
        return

    # 삭제 확인
    print("\n삭제할 파일:")
    for i, zip_file in enumerate(zip_files[:10]):
        print(f"  {i+1}. {zip_file.name}")
    if len(zip_files) > 10:
        print(f"  ... 외 {len(zip_files) - 10}개")

    # 삭제 실행
    deleted_count = 0
    total_size = 0

    for zip_file in zip_files:
        try:
            file_size = zip_file.stat().st_size
            zip_file.unlink()
            deleted_count += 1
            total_size += file_size
        except Exception as e:
            print(f"⚠️  삭제 실패: {zip_file} - {str(e)}")

    print(f"\n✅ 삭제 완료: {deleted_count:,}개 파일")
    print(f"   확보된 용량: {total_size / (1024*1024):.2f} MB")


def get_sample_traffic_files(source_dir: str, num_samples: int = 5) -> List[str]:
    """
    샘플 교통 관련 파일 찾기

    Args:
        source_dir: 소스 디렉토리
        num_samples: 샘플 수

    Returns:
        샘플 파일 경로 리스트
    """
    source_path = Path(source_dir)
    json_files = list(source_path.rglob("*.json"))

    samples = []
    for json_file in json_files:
        if check_traffic_related(str(json_file)):
            samples.append(str(json_file))
            if len(samples) >= num_samples:
                break

    return samples


def show_sample_content(file_path: str):
    """
    샘플 파일 내용 출력

    Args:
        file_path: 파일 경로
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"\n파일: {Path(file_path).name}")
        print("-" * 60)

        if 'info' in data:
            print(f"사건명: {data['info'].get('caseName', 'N/A')}")
            print(f"사건번호: {data['info'].get('caseNum', 'N/A')}")
            print(f"법원: {data['info'].get('courtName', 'N/A')}")

        if 'label' in data:
            print(f"\n질문: {data['label'].get('input', 'N/A')[:100]}...")
            print(f"답변: {data['label'].get('output', 'N/A')[:100]}...")

    except Exception as e:
        print(f"오류: {str(e)}")


if __name__ == "__main__":
    # 1. 샘플 확인
    print("=" * 60)
    print("교통 관련 샘플 파일 확인")
    print("=" * 60)

    samples = get_sample_traffic_files(".data", num_samples=3)

    if samples:
        print(f"\n{len(samples)}개 샘플 발견:")
        for sample in samples:
            show_sample_content(sample)
    else:
        print("\n교통 관련 파일을 찾지 못했습니다.")

    # 2. 필터링 및 복사
    print("\n\n")
    filter_and_copy_traffic_data(".data", ".data_traffic")

    # 3. ZIP 파일 삭제
    delete_zip_files(".data")

    print("\n" + "=" * 60)
    print("모든 작업 완료")
    print("=" * 60)
