import React from 'react';
import { Summary } from '../types';
import './SummarySection.css';

interface SummarySectionProps {
  summary: Summary | null;
  loading: boolean;
  error: string | null;
  onGenerate: () => void;
  generating: boolean;
}

const SummarySection: React.FC<SummarySectionProps> = ({
  summary,
  loading,
  error,
  onGenerate,
  generating,
}) => {
  return (
    <div className="summary-section">
      <div className="section-header">
        <h2>문서 요약</h2>
        {!summary && !loading && (
          <button
            className="btn-primary"
            onClick={onGenerate}
            disabled={generating}
          >
            {generating ? '요약 생성 중...' : '요약 생성'}
          </button>
        )}
      </div>

      {loading && (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>요약을 불러오는 중...</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <p>{error}</p>
        </div>
      )}

      {summary && !loading && (
        <div className="summary-content">
          <div className="summary-meta">
            <span className="meta-item">
              <strong>모델:</strong> {summary.llm_model}
            </span>
            <span className="meta-item">
              <strong>유형:</strong> {summary.summary_type}
            </span>
            <span className="meta-item">
              <strong>생성 일시:</strong>{' '}
              {new Date(summary.created_at).toLocaleString('ko-KR')}
            </span>
          </div>

          <div className="summary-text">
            <p>{summary.content}</p>
          </div>

          {summary.meta && Object.keys(summary.meta).length > 0 && (
            <div className="summary-metadata">
              <details>
                <summary>추가 정보</summary>
                <pre>{JSON.stringify(summary.meta, null, 2)}</pre>
              </details>
            </div>
          )}

          <button
            className="btn-secondary"
            onClick={onGenerate}
            disabled={generating}
          >
            {generating ? '재생성 중...' : '요약 재생성'}
          </button>
        </div>
      )}

      {!summary && !loading && !error && !generating && (
        <div className="empty-state">
          <p>아직 생성된 요약이 없습니다.</p>
          <p className="small">
            "요약 생성" 버튼을 클릭하여 문서의 핵심 내용을 요약해보세요.
          </p>
        </div>
      )}
    </div>
  );
};

export default SummarySection;
