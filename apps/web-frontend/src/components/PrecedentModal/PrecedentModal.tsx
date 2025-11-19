import React, { useState } from 'react';
import { FiX, FiCopy, FiCheck, FiFileText, FiCalendar, FiBook } from 'react-icons/fi';
import './PrecedentModal.css';

interface PrecedentModalProps {
  isOpen: boolean;
  onClose: () => void;
  precedentData: {
    id: string;
    source: string;
    title: string;
    type: string;
    case_number: string;
    date: string;
    citation: string;
    full_text: string;
    metadata: Record<string, any>;
  } | null;
  isLoading?: boolean;
}

const PrecedentModal: React.FC<PrecedentModalProps> = ({
  isOpen,
  onClose,
  precedentData,
  isLoading = false
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = async () => {
    if (precedentData?.full_text) {
      try {
        await navigator.clipboard.writeText(precedentData.full_text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    }
  };

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="precedent-modal-overlay" onClick={handleOverlayClick}>
      <div className="precedent-modal">
        <div className="precedent-modal-header">
          <div className="modal-header-left">
            <FiFileText className="modal-header-icon" />
            <h2 className="modal-title">판례 상세</h2>
          </div>
          <button
            className="modal-close-button"
            onClick={onClose}
            aria-label="Close modal"
          >
            <FiX />
          </button>
        </div>

        <div className="precedent-modal-body">
          {isLoading ? (
            <div className="modal-loading">
              <div className="loading-spinner"></div>
              <p>판례 내용을 불러오는 중...</p>
            </div>
          ) : precedentData ? (
            <>
              <div className="precedent-meta-section">
                <div className="meta-item">
                  <FiBook className="meta-icon" />
                  <div className="meta-content">
                    <div className="meta-label">제목</div>
                    <div className="meta-value">{precedentData.title || precedentData.source}</div>
                  </div>
                </div>

                {precedentData.case_number && (
                  <div className="meta-item">
                    <FiFileText className="meta-icon" />
                    <div className="meta-content">
                      <div className="meta-label">사건번호</div>
                      <div className="meta-value">{precedentData.case_number}</div>
                    </div>
                  </div>
                )}

                {precedentData.date && (
                  <div className="meta-item">
                    <FiCalendar className="meta-icon" />
                    <div className="meta-content">
                      <div className="meta-label">선고일</div>
                      <div className="meta-value">{precedentData.date}</div>
                    </div>
                  </div>
                )}

                {precedentData.citation && (
                  <div className="meta-item">
                    <FiBook className="meta-icon" />
                    <div className="meta-content">
                      <div className="meta-label">인용</div>
                      <div className="meta-value">{precedentData.citation}</div>
                    </div>
                  </div>
                )}
              </div>

              <div className="precedent-content-section">
                <div className="content-header">
                  <h3>전체 내용</h3>
                  <button
                    className={`copy-text-button ${copied ? 'copied' : ''}`}
                    onClick={handleCopy}
                    title="내용 복사"
                  >
                    {copied ? (
                      <>
                        <FiCheck /> 복사됨
                      </>
                    ) : (
                      <>
                        <FiCopy /> 복사
                      </>
                    )}
                  </button>
                </div>
                <div className="precedent-full-text">
                  {precedentData.full_text}
                </div>
              </div>
            </>
          ) : (
            <div className="modal-error">
              <p>판례 정보를 불러올 수 없습니다.</p>
            </div>
          )}
        </div>

        <div className="precedent-modal-footer">
          <button className="modal-footer-button" onClick={onClose}>
            닫기
          </button>
        </div>
      </div>
    </div>
  );
};

export default PrecedentModal;
