import React, { useState } from 'react';
import { KeyClause, ClauseType, AnalysisStatus } from '../types';
import { analyzeClauseSimilarity, getSimilarityLevel } from '../utils/similarity';
import './ClauseList.css';

interface PreviewClause {
  clause: KeyClause;
  similarity: number;
  similarTo: KeyClause | null;
  similarityLevel: ReturnType<typeof getSimilarityLevel>;
  isRecommendedToAdd: boolean;
  selected: boolean;
}

interface ClauseListProps {
  clauses: KeyClause[];
  loading: boolean;
  error: string | null;
  onExtract: () => void;
  extracting: boolean;
  // New props for preview mode
  previewClauses?: KeyClause[];
  previewLoading?: boolean;
  onExtractPreview?: () => void;
  onSaveSelected?: (clauses: KeyClause[]) => void;
  savingSelected?: boolean;
  onCancelPreview?: () => void;
  // Analysis status prop
  analysisStatus?: AnalysisStatus;
}

// Success message state
interface SuccessMessage {
  count: number;
  show: boolean;
}

const ClauseList: React.FC<ClauseListProps> = ({
  clauses,
  loading,
  error,
  onExtract,
  extracting,
  previewClauses,
  previewLoading,
  onExtractPreview,
  onSaveSelected,
  savingSelected,
  onCancelPreview,
  analysisStatus,
}) => {
  // Preview mode state
  const [previewData, setPreviewData] = useState<PreviewClause[]>([]);
  const [showPreview, setShowPreview] = useState(false);

  // Success message state
  const [successMessage, setSuccessMessage] = useState<SuccessMessage | null>(null);

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

  // Update preview data when previewClauses changes
  React.useEffect(() => {
    if (previewClauses && previewClauses.length > 0) {
      const analyzed = analyzeClauseSimilarity(previewClauses, clauses);
      const withSelection = analyzed.map(item => ({
        ...item,
        selected: item.isRecommendedToAdd, // Auto-select recommended clauses
      }));
      setPreviewData(withSelection);
      setShowPreview(true);
    }
  }, [previewClauses, clauses]);

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

  // Toggle selection
  const toggleSelection = (index: number) => {
    setPreviewData(prev =>
      prev.map((item, i) =>
        i === index ? { ...item, selected: !item.selected } : item
      )
    );
  };

  // Select all / Deselect all
  const selectAll = () => {
    setPreviewData(prev => prev.map(item => ({ ...item, selected: true })));
  };

  const deselectAll = () => {
    setPreviewData(prev => prev.map(item => ({ ...item, selected: false })));
  };

  // Handle save selected
  const handleSaveSelected = async () => {
    const selectedClauses = previewData
      .filter(item => item.selected)
      .map(item => item.clause);

    if (onSaveSelected && selectedClauses.length > 0) {
      onSaveSelected(selectedClauses);
      // Show success message
      setSuccessMessage({ count: selectedClauses.length, show: true });
    }
  };

  // Handle view clause list (go back to normal mode)
  const handleViewClauseList = () => {
    setShowPreview(false);
    setPreviewData([]);
    setSuccessMessage(null);
    if (onCancelPreview) {
      onCancelPreview();
    }
  };

  // Close success message
  const handleCloseSuccess = () => {
    setSuccessMessage(null);
  };

  // Handle cancel preview
  const handleCancelPreview = () => {
    setShowPreview(false);
    setPreviewData([]);
    if (onCancelPreview) {
      onCancelPreview();
    }
  };

  // Count selected
  const selectedCount = previewData.filter(item => item.selected).length;

  // Sort clauses by importance score
  const sortedClauses = [...clauses].sort(
    (a, b) => b.importance_score - a.importance_score
  );

  // Preview mode UI
  if (showPreview && previewData.length > 0) {
    return (
      <div className="clause-list-section">
        <div className="section-header">
          <h2>새로 추출된 조항</h2>
          <div className="preview-actions">
            <button className="btn-text" onClick={selectAll}>
              전체 선택
            </button>
            <button className="btn-text" onClick={deselectAll}>
              전체 해제
            </button>
          </div>
        </div>

        <div className="preview-info">
          <p>
            <strong>{previewData.length}개</strong>의 새 조항이 추출되었습니다.
            추가할 조항을 선택하세요.
          </p>
          <p className="preview-hint">
            기존 조항과 유사한 항목은 자동으로 해제되어 있습니다.
          </p>
        </div>

        <div className="clauses-grid preview-mode">
          {previewData.map((item, index) => (
            <div
              key={index}
              className={`clause-card preview-card ${item.selected ? 'selected' : ''}`}
              onClick={() => toggleSelection(index)}
            >
              <div className="clause-checkbox">
                <input
                  type="checkbox"
                  checked={item.selected}
                  onChange={() => toggleSelection(index)}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>

              <div className="clause-header">
                <div className="clause-type">
                  {clauseTypeLabels[item.clause.clause_type as ClauseType] || item.clause.clause_type}
                </div>
                <div className="similarity-info">
                  <span
                    className="similarity-badge"
                    style={{ backgroundColor: item.similarityLevel.color }}
                  >
                    {item.similarityLevel.label}
                  </span>
                  {item.similarity > 0 && (
                    <span className="similarity-score">
                      {Math.round(item.similarity * 100)}%
                    </span>
                  )}
                </div>
              </div>

              <h3 className="clause-title">{item.clause.title}</h3>

              <div className="clause-content">
                <p>{item.clause.content}</p>
              </div>

              {item.similarTo && item.similarity >= 0.2 && (
                <div className="similar-clause-info">
                  <span className="similar-label">유사 조항:</span>
                  <span className="similar-title">{item.similarTo.title}</span>
                </div>
              )}

              <div className="clause-footer">
                <span className="clause-score">
                  중요도: {item.clause.importance_score}/100
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="preview-footer">
          <div className="selection-summary">
            <strong>{selectedCount}</strong>개 선택됨
          </div>
          <div className="footer-actions">
            <button
              className="btn-secondary"
              onClick={handleCancelPreview}
              disabled={savingSelected}
            >
              취소
            </button>
            <button
              className="btn-primary"
              onClick={handleSaveSelected}
              disabled={selectedCount === 0 || savingSelected}
            >
              {savingSelected ? '저장 중...' : `선택한 조항 추가 (${selectedCount}개)`}
            </button>
          </div>
        </div>

        {/* Success message after saving */}
        {successMessage?.show && (
          <div className="success-message-container">
            <div className="success-message">
              <div className="success-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <div className="success-text">
                <strong>{successMessage.count}개</strong>의 조항이 추가되었습니다.
              </div>
              <div className="success-actions">
                <button
                  className="btn-success-primary"
                  onClick={handleViewClauseList}
                >
                  조항 목록 보기
                </button>
                <button
                  className="btn-success-secondary"
                  onClick={handleCloseSuccess}
                >
                  닫기
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Check if this step is currently being analyzed
  const isExtractingClauses = analysisStatus === 'extracting_clauses';

  // Normal mode UI
  return (
    <div className="clause-list-section">
      <div className="section-header">
        <h2>핵심 조항</h2>
        {clauses.length === 0 && !loading && !isExtractingClauses && (
          <button
            className="btn-primary"
            onClick={onExtract}
            disabled={extracting || previewLoading}
          >
            {extracting || previewLoading ? '조항 추출 중...' : '조항 추출'}
          </button>
        )}
      </div>

      {/* Analysis in progress banner for extracting_clauses */}
      {isExtractingClauses && (
        <div className="analysis-in-progress-banner">
          <div className="analysis-spinner"></div>
          <div className="analysis-info">
            <span className="analysis-step-badge">2/3</span>
            <span className="analysis-label">조항 추출 중...</span>
          </div>
          <p className="analysis-hint">문서에서 핵심 조항을 자동으로 추출하고 있습니다.</p>
        </div>
      )}

      {(loading || previewLoading) && !isExtractingClauses && (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>조항을 {previewLoading ? '추출하는' : '불러오는'} 중...</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <p>{error}</p>
        </div>
      )}

      {clauses.length > 0 && !loading && !previewLoading && (
        <>
          <div className="clause-summary">
            <p>
              총 <strong>{clauses.length}개</strong>의 핵심 조항이 추출되었습니다.
            </p>
            {onExtractPreview && (
              <button
                className="btn-secondary"
                onClick={onExtractPreview}
                disabled={extracting || previewLoading}
              >
                {previewLoading ? '추출 중...' : '새 조항 추출'}
              </button>
            )}
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

      {clauses.length === 0 && !loading && !error && !extracting && !previewLoading && (
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
