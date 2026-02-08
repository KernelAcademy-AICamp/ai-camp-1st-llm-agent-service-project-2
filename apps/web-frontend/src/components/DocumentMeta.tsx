import React from 'react';
import { UserDocumentDetail, RiskAnalysis, RiskSeverity } from '../types';
import '../styles/DocumentMeta.css';

interface DocumentMetaProps {
  document: UserDocumentDetail;
  onDelete: () => void;
  deleting: boolean;
  onBack: () => void;
  riskAnalysis: RiskAnalysis | null;
  riskLoading: boolean;
}

const DocumentMeta: React.FC<DocumentMetaProps> = ({
  document,
  onDelete,
  deleting,
  onBack,
  riskAnalysis,
  riskLoading,
}) => {
  const formatFileSize = (size: number | null): string => {
    if (!size) return '-';
    if (size < 1024 * 1024) {
      return `${(size / 1024).toFixed(1)} KB`;
    }
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusLabel = (status: string): { label: string; className: string } => {
    const statusMap: Record<string, { label: string; className: string }> = {
      UPLOADED: { label: '업로드됨', className: 'status-uploaded' },
      OCR_DONE: { label: 'OCR 완료', className: 'status-ocr' },
      PREPROCESSED: { label: '전처리됨', className: 'status-preprocessed' },
      EMBEDDED: { label: '임베딩 완료', className: 'status-embedded' },
      FAILED: { label: '실패', className: 'status-failed' },
    };
    return statusMap[status] || { label: status, className: 'status-default' };
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

  const getSeverityInfo = (severity: RiskSeverity): { label: string; className: string; color: string } => {
    const severityMap: Record<RiskSeverity, { label: string; className: string; color: string }> = {
      CRITICAL: { label: '심각', className: 'risk-critical', color: '#dc2626' },
      HIGH: { label: '높음', className: 'risk-high', color: '#ea580c' },
      MEDIUM: { label: '중간', className: 'risk-medium', color: '#ca8a04' },
      LOW: { label: '낮음', className: 'risk-low', color: '#65a30d' },
      INFO: { label: '정보', className: 'risk-info', color: '#0891b2' },
    };
    return severityMap[severity] || { label: severity, className: 'risk-default', color: '#6b7280' };
  };

  const getRiskScoreColor = (score: number): string => {
    if (score >= 70) return '#dc2626'; // red
    if (score >= 50) return '#f59e0b'; // yellow
    if (score >= 30) return '#3b82f6'; // blue
    return '#10b981'; // green
  };

  const statusInfo = getStatusLabel(document.status);

  return (
    <div className="document-meta">
      <button className="btn-back" onClick={onBack}>
        ← 목록
      </button>

      <h2 className="document-title">{document.title}</h2>

      <div className="meta-items">
        <div className="meta-item">
          <span className="meta-label">상태</span>
          <span className={`status-badge ${statusInfo.className}`}>
            {statusInfo.label}
          </span>
        </div>

        <div className="meta-item">
          <span className="meta-label">유형</span>
          <span className="meta-value">{getDocTypeLabel(document.doc_type)}</span>
        </div>

        <div className="meta-item">
          <span className="meta-label">언어</span>
          <span className="meta-value">
            {document.language === 'ko' ? '한국어' : '영어'}
          </span>
        </div>

        {document.file_size && (
          <div className="meta-item">
            <span className="meta-label">파일 크기</span>
            <span className="meta-value">{formatFileSize(document.file_size)}</span>
          </div>
        )}

        {document.file_type && (
          <div className="meta-item">
            <span className="meta-label">파일 타입</span>
            <span className="meta-value">{document.file_type.toUpperCase()}</span>
          </div>
        )}

        {document.page_count && (
          <div className="meta-item">
            <span className="meta-label">페이지</span>
            <span className="meta-value">{document.page_count}쪽</span>
          </div>
        )}

        <div className="meta-item">
          <span className="meta-label">청크 수</span>
          <span className="meta-value">{document.chunk_count}개</span>
        </div>

        <div className="meta-item">
          <span className="meta-label">업로드</span>
          <span className="meta-value meta-date">{formatDate(document.created_at)}</span>
        </div>
      </div>

      {/* Risk Summary Section - Key design requirement */}
      <div className="risk-summary-section">
        <h3 className="risk-summary-title">리스크 요약</h3>
        {riskLoading ? (
          <div className="risk-loading">
            <div className="risk-spinner"></div>
            <span>분석 로딩 중...</span>
          </div>
        ) : riskAnalysis ? (
          <div className="risk-summary-content">
            <div className="risk-score-display">
              <div
                className="risk-score-bar"
                style={{
                  background: `linear-gradient(to right, ${getRiskScoreColor(riskAnalysis.overall_risk_score)} ${riskAnalysis.overall_risk_score}%, #e5e7eb ${riskAnalysis.overall_risk_score}%)`,
                }}
              />
              <div className="risk-score-info">
                <span
                  className="risk-score-value"
                  style={{ color: getRiskScoreColor(riskAnalysis.overall_risk_score) }}
                >
                  {riskAnalysis.overall_risk_score}점
                </span>
                <span
                  className={`risk-severity-badge ${getSeverityInfo(riskAnalysis.severity).className}`}
                  style={{ backgroundColor: getSeverityInfo(riskAnalysis.severity).color }}
                >
                  {getSeverityInfo(riskAnalysis.severity).label}
                </span>
              </div>
            </div>
            <div className="risk-item-count">
              위험 항목: {riskAnalysis.risk_items.length}개
            </div>
          </div>
        ) : (
          <div className="risk-no-data">
            <span>분석 없음</span>
            <span className="risk-hint">우측 패널에서 분석 실행</span>
          </div>
        )}
      </div>

      {document.error_message && (
        <div className="meta-error">
          <strong>오류:</strong> {document.error_message}
        </div>
      )}

      {/* Processing status indicators */}
      {document.status !== 'EMBEDDED' && document.status !== 'FAILED' && (
        <div className="meta-processing">
          처리 중...
        </div>
      )}

      {document.is_processing_complete && (
        <div className="meta-complete">
          RAG 검색 사용 가능
        </div>
      )}

      <div className="meta-actions">
        <button
          className="btn-delete"
          onClick={onDelete}
          disabled={deleting}
        >
          {deleting ? '삭제 중...' : '문서 삭제'}
        </button>
      </div>
    </div>
  );
};

export default DocumentMeta;
