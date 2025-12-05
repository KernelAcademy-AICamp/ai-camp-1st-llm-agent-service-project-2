/**
 * PrecedentCompare Component
 *
 * 판례 비교 컴포넌트
 * - 최대 3개 판례 선택 가능
 * - 비교 테이블 표시
 * - 현재 사건과 비교 기능
 */

import React, { useState, useMemo } from 'react';
import { CriminalPrecedent, SentencingFactors } from '../../../types';

interface PrecedentCompareProps {
  precedents: CriminalPrecedent[];
  currentCase?: {
    crimeType: string;
    factors: SentencingFactors;
  };
  onSelectPrecedent?: (precedent: CriminalPrecedent) => void;
}

const PrecedentCompare: React.FC<PrecedentCompareProps> = ({
  precedents,
  currentCase,
  onSelectPrecedent,
}) => {
  const [selectedPrecedents, setSelectedPrecedents] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<'relevance' | 'date' | 'sentence'>('relevance');

  const toggleSelect = (caseNumber: string) => {
    setSelectedPrecedents(prev => {
      if (prev.includes(caseNumber)) {
        return prev.filter(c => c !== caseNumber);
      }
      // 최대 3개까지 선택 가능
      if (prev.length < 3) {
        return [...prev, caseNumber];
      }
      return prev;
    });
  };

  const clearSelection = () => {
    setSelectedPrecedents([]);
  };

  const selectedData = useMemo(() => {
    return precedents.filter(p => selectedPrecedents.includes(p.case_number));
  }, [precedents, selectedPrecedents]);

  const sortedPrecedents = useMemo(() => {
    const sorted = [...precedents];
    switch (sortBy) {
      case 'relevance':
        return sorted.sort((a, b) => b.relevance - a.relevance);
      case 'date':
        return sorted.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
      case 'sentence':
        // 형량 정렬 (간단한 문자열 비교)
        return sorted.sort((a, b) => a.sentence.localeCompare(b.sentence));
      default:
        return sorted;
    }
  }, [precedents, sortBy]);

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getRelevanceClass = (relevance: number): string => {
    if (relevance >= 80) return 'high';
    if (relevance >= 60) return 'medium';
    return 'low';
  };

  if (precedents.length === 0) {
    return (
      <div className="precedent-compare empty">
        <p>비교할 판례가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="precedent-compare">
      <div className="compare-header">
        <h2>판례 비교</h2>
        <p className="description">
          비교할 판례를 최대 3개까지 선택하세요. 선택한 판례들의 주요 정보를 비교합니다.
        </p>
      </div>

      {/* 정렬 및 선택 컨트롤 */}
      <div className="compare-controls">
        <div className="sort-control">
          <label>정렬 기준:</label>
          <select value={sortBy} onChange={e => setSortBy(e.target.value as any)}>
            <option value="relevance">관련도순</option>
            <option value="date">최신순</option>
            <option value="sentence">형량순</option>
          </select>
        </div>
        <div className="selection-info">
          <span className="selected-count">
            {selectedPrecedents.length}/3 선택됨
          </span>
          {selectedPrecedents.length > 0 && (
            <button className="clear-btn" onClick={clearSelection}>
              선택 해제
            </button>
          )}
        </div>
      </div>

      {/* 판례 선택 목록 */}
      <div className="precedent-list">
        {sortedPrecedents.map(p => (
          <div
            key={p.case_number}
            className={`precedent-item ${selectedPrecedents.includes(p.case_number) ? 'selected' : ''}`}
            onClick={() => toggleSelect(p.case_number)}
          >
            <div className="item-checkbox">
              <input
                type="checkbox"
                checked={selectedPrecedents.includes(p.case_number)}
                onChange={() => toggleSelect(p.case_number)}
                disabled={
                  !selectedPrecedents.includes(p.case_number) &&
                  selectedPrecedents.length >= 3
                }
              />
            </div>
            <div className="item-content">
              <div className="item-header">
                <span className="court">{p.court}</span>
                <span className="case-number">{p.case_number}</span>
                <span className="date">{formatDate(p.date)}</span>
              </div>
              <div className="item-body">
                <span className="crime-type">{p.crime_type}</span>
                <span className="sentence">{p.sentence}</span>
              </div>
              <div className="item-summary">{p.summary}</div>
            </div>
            <div className="item-relevance">
              <span className={`relevance-badge ${getRelevanceClass(p.relevance)}`}>
                {p.relevance}%
              </span>
              <span className="relevance-label">관련도</span>
            </div>
          </div>
        ))}
      </div>

      {/* 비교 테이블 */}
      {selectedData.length > 0 && (
        <div className="compare-table-container">
          <h3>선택된 판례 비교</h3>
          <div className="compare-table-wrapper">
            <table className="compare-table">
              <thead>
                <tr>
                  <th>항목</th>
                  {selectedData.map(p => (
                    <th key={p.case_number}>
                      <div className="th-content">
                        <span className="th-case-number">{p.case_number}</span>
                        <button
                          className="remove-btn"
                          onClick={e => {
                            e.stopPropagation();
                            toggleSelect(p.case_number);
                          }}
                        >
                          x
                        </button>
                      </div>
                    </th>
                  ))}
                  {currentCase && <th className="current-case">현재 사건</th>}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="row-label">법원</td>
                  {selectedData.map(p => (
                    <td key={p.case_number}>{p.court}</td>
                  ))}
                  {currentCase && <td>-</td>}
                </tr>
                <tr>
                  <td className="row-label">판결일</td>
                  {selectedData.map(p => (
                    <td key={p.case_number}>{formatDate(p.date)}</td>
                  ))}
                  {currentCase && <td>-</td>}
                </tr>
                <tr>
                  <td className="row-label">범죄 유형</td>
                  {selectedData.map(p => (
                    <td key={p.case_number}>{p.crime_type}</td>
                  ))}
                  {currentCase && <td>{currentCase.crimeType}</td>}
                </tr>
                <tr>
                  <td className="row-label">선고</td>
                  {selectedData.map(p => (
                    <td key={p.case_number} className="sentence-cell">
                      {p.sentence}
                    </td>
                  ))}
                  {currentCase && <td className="pending">미정</td>}
                </tr>
                <tr>
                  <td className="row-label">관련도</td>
                  {selectedData.map(p => (
                    <td key={p.case_number}>
                      <span className={`relevance-badge ${getRelevanceClass(p.relevance)}`}>
                        {p.relevance}%
                      </span>
                    </td>
                  ))}
                  {currentCase && <td>-</td>}
                </tr>
              </tbody>
            </table>
          </div>

          {/* 판례 요약 비교 */}
          <div className="summary-comparison">
            <h4>요약 비교</h4>
            <div className="summary-cards">
              {selectedData.map(p => (
                <div key={p.case_number} className="summary-card">
                  <div className="card-header">
                    <span className="case-number">{p.case_number}</span>
                    <span className={`relevance-badge ${getRelevanceClass(p.relevance)}`}>
                      {p.relevance}%
                    </span>
                  </div>
                  <p className="summary-text">{p.summary}</p>
                  {onSelectPrecedent && (
                    <button
                      className="view-detail-btn"
                      onClick={() => onSelectPrecedent(p)}
                    >
                      상세 보기
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 도움말 */}
      <div className="compare-help">
        <span className="icon">*</span>
        <span>
          관련도는 범죄 유형, 범행 태양, 피고인 특성 등을 종합적으로 고려하여 산정됩니다.
        </span>
      </div>
    </div>
  );
};

export default PrecedentCompare;
