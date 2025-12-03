import React, { useState, useEffect } from 'react';
import { FiX, FiCheck, FiAlertTriangle, FiFileText, FiEdit3 } from 'react-icons/fi';
import './OCRReviewModal.css';

export interface ExtractionResult {
  success: boolean;
  text: string;
  extraction_method: string;  // 'pymupdf' | 'ocr' | 'docx' | 'txt'
  needs_review: boolean;
  confidence: number;
  file_type: string;
  metadata?: {
    page_count?: number;
    char_count?: number;
    avg_confidence?: number;
    preprocessing?: string;
  };
  error?: string;
}

interface OCRReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (text: string) => void;
  extractionResult: ExtractionResult | null;
  isLoading?: boolean;
  fileName?: string;
}

const OCRReviewModal: React.FC<OCRReviewModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  extractionResult,
  isLoading = false,
  fileName = ''
}) => {
  const [editedText, setEditedText] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (extractionResult?.text) {
      setEditedText(extractionResult.text);
    }
  }, [extractionResult]);

  if (!isOpen) return null;

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleConfirm = () => {
    onConfirm(editedText);
  };

  const getExtractionMethodLabel = (method: string): string => {
    switch (method) {
      case 'pymupdf':
        return 'PDF 직접 추출';
      case 'ocr':
        return 'OCR 인식';
      case 'docx':
        return 'DOCX 추출';
      case 'txt':
        return '텍스트 파일';
      default:
        return method;
    }
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 80) return '#22c55e';
    if (confidence >= 60) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="ocr-modal-overlay" onClick={handleOverlayClick}>
      <div className="ocr-modal">
        <div className="ocr-modal-header">
          <div className="modal-header-left">
            <FiFileText className="modal-header-icon" />
            <h2 className="modal-title">
              {extractionResult?.needs_review ? 'OCR 추출 결과 확인' : '텍스트 추출 결과 확인'}
            </h2>
          </div>
          <button
            className="modal-close-button"
            onClick={onClose}
            aria-label="Close modal"
          >
            <FiX />
          </button>
        </div>

        <div className="ocr-modal-body">
          {isLoading ? (
            <div className="modal-loading">
              <div className="loading-spinner"></div>
              <p>텍스트를 추출하는 중...</p>
            </div>
          ) : extractionResult ? (
            <>
              {/* Meta Information */}
              <div className="ocr-meta-section">
                {fileName && (
                  <div className="meta-item">
                    <span className="meta-label">파일:</span>
                    <span className="meta-value">{fileName}</span>
                  </div>
                )}
                <div className="meta-item">
                  <span className="meta-label">추출 방법:</span>
                  <span className={`meta-badge method-${extractionResult.extraction_method}`}>
                    {getExtractionMethodLabel(extractionResult.extraction_method)}
                  </span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">신뢰도:</span>
                  <span
                    className="confidence-badge"
                    style={{ backgroundColor: getConfidenceColor(extractionResult.confidence) }}
                  >
                    {extractionResult.confidence.toFixed(1)}%
                  </span>
                </div>
                {extractionResult.metadata?.page_count && (
                  <div className="meta-item">
                    <span className="meta-label">페이지:</span>
                    <span className="meta-value">{extractionResult.metadata.page_count}</span>
                  </div>
                )}
                <div className="meta-item">
                  <span className="meta-label">글자 수:</span>
                  <span className="meta-value">
                    {(extractionResult.metadata?.char_count || editedText.length).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Warning for OCR results */}
              {extractionResult.needs_review && (
                <div className="ocr-warning">
                  <FiAlertTriangle className="warning-icon" />
                  <div className="warning-content">
                    <strong>OCR 인식 결과</strong>
                    <p>
                      이 텍스트는 OCR로 추출되었습니다. 진행하기 전에 오류가 없는지 검토하고 수정해 주세요.
                    </p>
                  </div>
                </div>
              )}

              {/* Text Content */}
              <div className="ocr-content-section">
                <div className="content-header">
                  <h3>추출된 텍스트</h3>
                  <button
                    className={`edit-toggle-button ${isEditing ? 'editing' : ''}`}
                    onClick={() => setIsEditing(!isEditing)}
                  >
                    <FiEdit3 />
                    {isEditing ? '보기 모드' : '편집 모드'}
                  </button>
                </div>

                {isEditing ? (
                  <textarea
                    className="ocr-text-editor"
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                    placeholder="추출된 텍스트를 입력하거나 수정하세요..."
                  />
                ) : (
                  <div className="ocr-text-viewer">
                    {editedText || '추출된 텍스트가 없습니다'}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="modal-error">
              <p>추출 결과를 불러올 수 없습니다.</p>
            </div>
          )}
        </div>

        <div className="ocr-modal-footer">
          <button className="modal-cancel-button" onClick={onClose}>
            취소
          </button>
          <button
            className="modal-confirm-button"
            onClick={handleConfirm}
            disabled={!editedText.trim() || isLoading}
          >
            <FiCheck />
            확인 및 분석하기
          </button>
        </div>
      </div>
    </div>
  );
};

export default OCRReviewModal;
