import React from 'react';
import { KeyClause, ClauseType } from '../types';
import './ClauseList.css';

interface ClauseListProps {
  clauses: KeyClause[];
  loading: boolean;
  error: string | null;
  onExtract: () => void;
  extracting: boolean;
}

const ClauseList: React.FC<ClauseListProps> = ({
  clauses,
  loading,
  error,
  onExtract,
  extracting,
}) => {
  // Clause type labels in Korean
  const clauseTypeLabels: Record<ClauseType, string> = {
    PAYMENT: '지급 조항',
    OBLIGATION: '의무 조항',
    TERMINATION: '해지 조항',
    LIABILITY: '책임 조항',
    WARRANTY: '보증 조항',
    CONFIDENTIALITY: '기밀유지 조항',
    DISPUTE: '분쟁해결 조항',
    IP: '지식재산권 조항',
    DELIVERY: '인도 조항',
    OTHER: '기타 조항',
  };

  // Importance level badge
  const getImportanceBadge = (score: number) => {
    if (score >= 80) {
      return <span className="importance-badge high">매우 중요</span>;
    } else if (score >= 60) {
      return <span className="importance-badge medium">중요</span>;
    } else {
      return <span className="importance-badge low">보통</span>;
    }
  };

  // Sort clauses by importance score
  const sortedClauses = [...clauses].sort(
    (a, b) => b.importance_score - a.importance_score
  );

  return (
    <div className="clause-list-section">
      <div className="section-header">
        <h2>📋 핵심 조항</h2>
        {clauses.length === 0 && !loading && (
          <button
            className="btn-primary"
            onClick={onExtract}
            disabled={extracting}
          >
            {extracting ? '조항 추출 중...' : '조항 추출'}
          </button>
        )}
      </div>

      {loading && (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>조항을 불러오는 중...</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <p>⚠️ {error}</p>
        </div>
      )}

      {clauses.length > 0 && !loading && (
        <>
          <div className="clause-summary">
            <p>
              총 <strong>{clauses.length}개</strong>의 핵심 조항이 추출되었습니다.
            </p>
            <button
              className="btn-secondary"
              onClick={onExtract}
              disabled={extracting}
            >
              {extracting ? '재추출 중...' : '조항 재추출'}
            </button>
          </div>

          <div className="clauses-grid">
            {sortedClauses.map((clause) => (
              <div key={clause.id} className="clause-card">
                <div className="clause-header">
                  <div className="clause-type">
                    {clauseTypeLabels[clause.clause_type]}
                  </div>
                  {getImportanceBadge(clause.importance_score)}
                </div>

                <h3 className="clause-title">{clause.title}</h3>

                <div className="clause-content">
                  <p>{clause.content}</p>
                </div>

                <div className="clause-footer">
                  <span className="clause-score">
                    중요도: {clause.importance_score}/100
                  </span>
                  <span className="clause-model">{clause.llm_model}</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {clauses.length === 0 && !loading && !error && !extracting && (
        <div className="empty-state">
          <p>아직 추출된 조항이 없습니다.</p>
          <p className="small">
            "조항 추출" 버튼을 클릭하여 문서의 핵심 조항을 추출해보세요.
          </p>
        </div>
      )}
    </div>
  );
};

export default ClauseList;
