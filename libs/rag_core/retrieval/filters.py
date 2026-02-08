"""
Retrieval Filters
검색 결과 필터링 (순수 로직, DB 비의존)
"""

from typing import List, Dict, Any, Set


def filter_results(
    results: List[Dict[str, Any]],
    excluded_ids: Set[str],
    id_key: str = 'source'
) -> List[Dict[str, Any]]:
    """
    검색 결과 필터링

    excluded_ids에 포함된 ID를 가진 결과를 제거합니다.

    Args:
        results: 검색 결과 리스트
        excluded_ids: 제외할 ID 집합
        id_key: 결과에서 ID를 가져올 키 (기본: 'source')

    Returns:
        필터링된 검색 결과

    Example:
        >>> results = [
        ...     {"source": "doc1", "content": "..."},
        ...     {"source": "doc2", "content": "..."},
        ...     {"source": "doc3", "content": "..."}
        ... ]
        >>> excluded = {"doc2"}
        >>> filtered = filter_results(results, excluded)
        >>> len(filtered)
        2
    """
    if not excluded_ids:
        return results

    filtered = []
    for result in results:
        doc_id = result.get(id_key)
        if doc_id and doc_id not in excluded_ids:
            filtered.append(result)

    return filtered
