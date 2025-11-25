import React from 'react';
import { UserDocumentDetail } from '../types';
import '../styles/DocumentMeta.css';

interface DocumentMetaProps {
  document: UserDocumentDetail;
  onDelete: () => void;
  deleting: boolean;
  onBack: () => void;
}

const DocumentMeta: React.FC<DocumentMetaProps> = ({
  document,
  onDelete,
  deleting,
  onBack,
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
