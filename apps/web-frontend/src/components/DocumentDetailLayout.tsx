import React, { useState, useEffect } from 'react';
import { UserDocumentDetail, Summary, KeyClause, RiskAnalysis } from '../types';
import DocumentViewer from './DocumentViewer';
import AnalysisPanel from './AnalysisPanel';
import '../styles/DocumentDetailLayout.css';

interface DocumentDetailLayoutProps {
  document: UserDocumentDetail;
  token?: string;
  fileUrl?: string;
  onDelete: () => void;
  deleting: boolean;
  onBack: () => void;
  // Summary props
  summary: Summary | null;
  summaryLoading: boolean;
  summaryError: string | null;
  onGenerateSummary: () => void;
  generatingSummary: boolean;
  // Clauses props
  clauses: KeyClause[];
  clausesLoading: boolean;
  clausesError: string | null;
  onExtractClauses: () => void;
  extractingClauses: boolean;
  // Risk props
  riskAnalysis: RiskAnalysis | null;
  riskLoading: boolean;
}

const DocumentDetailLayout: React.FC<DocumentDetailLayoutProps> = ({
  document,
  token,
  fileUrl,
  onDelete,
  deleting,
  onBack,
  summary,
  summaryLoading,
  summaryError,
  onGenerateSummary,
  generatingSummary,
  clauses,
  clausesLoading,
  clausesError,
  onExtractClauses,
  extractingClauses,
  riskAnalysis,
  riskLoading,
}) => {
  // PDF 파일인지 확인 (file_type이 'pdf' 또는 'application/pdf'인 경우)
  const isPdf = document.file_type?.toLowerCase().includes('pdf') || false;
  const canShowOriginal = isPdf && fileUrl;

  // 원문 보기 슬라이드 패널 상태
  const [showDocumentPanel, setShowDocumentPanel] = useState(false);
  // 문서 뷰 모드: PDF 파일이면 원본(PDF)으로 기본, 아니면 텍스트
  const [viewMode, setViewMode] = useState<'original' | 'text'>(
    canShowOriginal ? 'original' : 'text'
  );

  // 문서가 변경되면 viewMode 초기화
  useEffect(() => {
    setViewMode(canShowOriginal ? 'original' : 'text');
  }, [document.id, canShowOriginal]);

  const formatFileSize = (size: number | null): string => {
    if (!size) return '-';
    if (size < 1024 * 1024) {
      return `${(size / 1024).toFixed(1)} KB`;
    }
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { label: string; className: string }> = {
      UPLOADED: { label: '업로드됨', className: 'badge-uploaded' },
      OCR_DONE: { label: 'OCR 완료', className: 'badge-processing' },
      PREPROCESSED: { label: '전처리됨', className: 'badge-processing' },
      EMBEDDED: { label: '분석 완료', className: 'badge-completed' },
      FAILED: { label: '실패', className: 'badge-failed' },
    };
    return statusMap[status] || { label: status, className: 'badge-default' };
  };

  const getDocTypeLabel = (docType: string): string => {
    const typeMap: Record<string, string> = {
      CASE: '사건',
      CONTRACT: '계약서',
      STATUTE: '법령',
      PRECEDENT: '판례',
      OTHER: '기타',
    };
    return typeMap[docType] || docType;
  };

  const statusInfo = getStatusBadge(document.status);

  return (
    <div className="document-detail-layout-v3">
      {/* Header - research/cases와 유사한 스타일 */}
      <header className="detail-header-compact">
        <div className="header-left">
          <h1 className="header-title">{document.title}</h1>
          <span className="header-meta-inline">
            <span className="meta-tag">{getDocTypeLabel(document.doc_type)}</span>
            <span className="meta-divider">·</span>
            <span>{formatFileSize(document.file_size)}</span>
            {riskAnalysis && (
              <>
                <span className="meta-divider">·</span>
                <span className="risk-score-mini">
                  리스크 {riskAnalysis.overall_risk_score}점
                </span>
              </>
            )}
          </span>
        </div>
        <div className="header-actions">
          <button
            className="btn-view-document"
            onClick={() => setShowDocumentPanel(true)}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            원문
          </button>
          <button
            className="btn-delete"
            onClick={onDelete}
            disabled={deleting}
          >
            {deleting ? '삭제 중...' : '삭제'}
          </button>
        </div>
      </header>

      {/* AI Analysis - 메인 콘텐츠 (AnalysisPanel 직접 렌더링) */}
      <main className="analysis-main">
        <AnalysisPanel
          document={document}
          token={token}
          summary={summary}
          summaryLoading={summaryLoading}
          summaryError={summaryError}
          onGenerateSummary={onGenerateSummary}
          generatingSummary={generatingSummary}
          clauses={clauses}
          clausesLoading={clausesLoading}
          clausesError={clausesError}
          onExtractClauses={onExtractClauses}
          extractingClauses={extractingClauses}
        />
      </main>

      {/* Document Slide Panel */}
      {showDocumentPanel && (
        <div className="document-panel-overlay" onClick={() => setShowDocumentPanel(false)}>
          <aside className="document-slide-panel" onClick={(e) => e.stopPropagation()}>
            <div className="panel-header">
              <div className="panel-header-left">
                <h2>문서 원문</h2>
                {canShowOriginal && (
                  <div className="viewer-mode-toggle">
                    <button
                      className={`toggle-btn ${viewMode === 'original' ? 'active' : ''}`}
                      onClick={() => setViewMode('original')}
                    >
                      PDF
                    </button>
                    <button
                      className={`toggle-btn ${viewMode === 'text' ? 'active' : ''}`}
                      onClick={() => setViewMode('text')}
                    >
                      텍스트
                    </button>
                  </div>
                )}
              </div>
              <button className="btn-close-panel" onClick={() => setShowDocumentPanel(false)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="panel-body">
              <DocumentViewer
                document={document}
                fileUrl={fileUrl}
                viewMode={canShowOriginal ? viewMode : 'text'}
              />
            </div>
          </aside>
        </div>
      )}
    </div>
  );
};

export default DocumentDetailLayout;
