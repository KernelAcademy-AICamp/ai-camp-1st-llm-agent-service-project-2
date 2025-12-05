import React, { useState, useEffect, useCallback } from 'react';
import { FiBookOpen, FiCalendar, FiMapPin, FiPercent, FiRefreshCw } from 'react-icons/fi';
import { CriminalPrecedent } from '../../../types';
import { apiClient } from '../../../api/client';
import './CriminalAnalysis.css';

interface RelatedCasesSectionProps {
  documentId: string;
  token?: string;
  crimeType?: string;
  // Pre-loaded data (optional)
  initialPrecedents?: CriminalPrecedent[];
}

const RelatedCasesSection: React.FC<RelatedCasesSectionProps> = ({
  documentId,
  token,
  crimeType,
  initialPrecedents
}) => {
  const [precedents, setPrecedents] = useState<CriminalPrecedent[]>(initialPrecedents || []);
  const [loading, setLoading] = useState(!initialPrecedents);
  const [error, setError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [selectedPrecedents, setSelectedPrecedents] = useState<Set<string>>(new Set());

  const loadPrecedents = useCallback(async () => {
    if (!documentId || !token) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getCriminalAnalysis(documentId, token);
      if (response.related_precedents) {
        setPrecedents(response.related_precedents);
      }
    } catch (err: any) {
      console.log('No related precedents found for document:', documentId);
    } finally {
      setLoading(false);
    }
  }, [documentId, token]);

  useEffect(() => {
    if (!initialPrecedents) {
      loadPrecedents();
    }
  }, [loadPrecedents, initialPrecedents]);

  const handleSearch = async () => {
    if (!documentId || !token) return;

    setSearching(true);
    setError(null);

    try {
      const response = await apiClient.searchRelatedPrecedents(documentId, token, crimeType);
      if (response.precedents) {
        setPrecedents(response.precedents);
      }
    } catch (err: any) {
      setError(err.message || '유사 판례 검색에 실패했습니다.');
    } finally {
      setSearching(false);
    }
  };

  const getRelevanceColor = (relevance: number) => {
    if (relevance >= 80) return '#10b981';
    if (relevance >= 60) return '#3b82f6';
    if (relevance >= 40) return '#f59e0b';
    return '#9ca3af';
  };

  const toggleSelect = (caseNumber: string) => {
    setSelectedPrecedents(prev => {
      const newSet = new Set(prev);
      if (newSet.has(caseNumber)) {
        newSet.delete(caseNumber);
      } else if (newSet.size < 3) {
        newSet.add(caseNumber);
      }
      return newSet;
    });
  };

  const selectedData = precedents.filter(p => selectedPrecedents.has(p.case_number));

  if (loading) {
    return (
      <div className="criminal-section related-cases-section">
        <div className="section-header">
          <div className="section-title">
            <FiBookOpen className="section-icon" />
            <h3>유사 판례</h3>
          </div>
        </div>
        <div className="section-content">
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>유사 판례를 검색하는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (precedents.length === 0) {
    return (
      <div className="criminal-section related-cases-section">
        <div className="section-header">
          <div className="section-title">
            <FiBookOpen className="section-icon" />
            <h3>유사 판례</h3>
          </div>
        </div>
        <div className="section-content">
          <div className="empty-state">
            <FiBookOpen className="empty-icon" />
            <p>유사 판례가 아직 검색되지 않았습니다.</p>
            <button
              className="btn-analyze"
              onClick={handleSearch}
              disabled={searching}
            >
              {searching ? (
                <>
                  <FiRefreshCw className="icon-spin" />
                  검색 중...
                </>
              ) : (
                '유사 판례 검색하기'
              )}
            </button>
            {error && <p className="error-message">{error}</p>}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="criminal-section related-cases-section">
      <div className="section-header">
        <div className="section-title">
          <FiBookOpen className="section-icon" />
          <h3>유사 판례</h3>
        </div>
        <span className="precedent-count">{precedents.length}건</span>
      </div>

      <div className="section-content">
        <p className="section-description">
          클릭하여 판례를 선택하면 비교할 수 있습니다 (최대 3건)
        </p>

        {/* 판례 목록 */}
        <div className="precedents-list">
          {precedents.map((precedent, idx) => (
            <div
              key={idx}
              className={`precedent-item ${selectedPrecedents.has(precedent.case_number) ? 'selected' : ''}`}
              onClick={() => toggleSelect(precedent.case_number)}
            >
              <div className="precedent-header">
                <div className="precedent-info">
                  <input
                    type="checkbox"
                    checked={selectedPrecedents.has(precedent.case_number)}
                    onChange={() => toggleSelect(precedent.case_number)}
                    onClick={e => e.stopPropagation()}
                  />
                  <span className="case-number">{precedent.case_number || '사건번호 미상'}</span>
                  <span className="crime-type-badge">{precedent.crime_type}</span>
                </div>
                <div
                  className="relevance-badge"
                  style={{ backgroundColor: `${getRelevanceColor(precedent.relevance)}20`, color: getRelevanceColor(precedent.relevance) }}
                >
                  <FiPercent />
                  <span>{precedent.relevance.toFixed(0)}%</span>
                </div>
              </div>

              <div className="precedent-meta">
                {precedent.court && (
                  <span className="meta-item">
                    <FiMapPin />
                    {precedent.court}
                  </span>
                )}
                {precedent.date && (
                  <span className="meta-item">
                    <FiCalendar />
                    {precedent.date}
                  </span>
                )}
              </div>

              {precedent.sentence && (
                <div className="precedent-sentence">
                  <span className="sentence-label">선고</span>
                  <span className="sentence-value">{precedent.sentence}</span>
                </div>
              )}

              {precedent.summary && (
                <p className="precedent-summary">{precedent.summary}</p>
              )}
            </div>
          ))}
        </div>

        {/* 비교 테이블 */}
        {selectedData.length > 0 && (
          <div className="compare-section">
            <h4>선택된 판례 비교</h4>
            <div className="compare-table-wrapper">
              <table className="compare-table">
                <thead>
                  <tr>
                    <th>항목</th>
                    {selectedData.map(p => (
                      <th key={p.case_number}>{p.case_number}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>법원</td>
                    {selectedData.map(p => (
                      <td key={p.case_number}>{p.court || '-'}</td>
                    ))}
                  </tr>
                  <tr>
                    <td>범죄 유형</td>
                    {selectedData.map(p => (
                      <td key={p.case_number}>{p.crime_type}</td>
                    ))}
                  </tr>
                  <tr>
                    <td>선고일</td>
                    {selectedData.map(p => (
                      <td key={p.case_number}>{p.date || '-'}</td>
                    ))}
                  </tr>
                  <tr>
                    <td>선고</td>
                    {selectedData.map(p => (
                      <td key={p.case_number} className="sentence-cell">{p.sentence}</td>
                    ))}
                  </tr>
                  <tr>
                    <td>관련도</td>
                    {selectedData.map(p => (
                      <td key={p.case_number}>
                        <span style={{ color: getRelevanceColor(p.relevance) }}>
                          {p.relevance.toFixed(0)}%
                        </span>
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        <button
          className="btn-refresh"
          onClick={handleSearch}
          disabled={searching}
        >
          {searching ? (
            <>
              <FiRefreshCw className="icon-spin" />
              검색 중...
            </>
          ) : (
            <>
              <FiRefreshCw />
              재검색
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default RelatedCasesSection;
