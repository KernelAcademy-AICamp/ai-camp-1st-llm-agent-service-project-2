/**
 * Agent Hub - Input Area Component (ChatGPT Style)
 *
 * 메시지 입력창, 파일 첨부, 전송 버튼
 * 깔끔하고 중앙 정렬된 디자인
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { cn } from '../../../lib/utils';
import { ExecutionStatus } from './AppLayout';
import { agentHubService } from '../../../services/agentHubService';
import type { AttachmentPayload } from '../../../types/agentHub';
import { ProgressIndicator } from '../messages/ProgressIndicator';

type AttachmentStatus = 'processing' | 'ready' | 'error';

interface Attachment {
  id: string;
  file?: File;  // 새 파일 첨부 시
  documentId?: string;  // 기존 문서 선택 시
  name: string;
  size: number;
  type: string;
  status: AttachmentStatus;
  processed?: {
    content: string;
    docType?: string;
    metadata?: Record<string, any>;
  };
  error?: string;
  isExistingDocument?: boolean;  // 기존 문서 여부
}

// 기존 문서 타입
interface ExistingDocument {
  id: string;
  title: string;
  doc_type: string;
  created_at: string;
  file_size?: number;
  status?: string;
}

interface InputAreaProps {
  onSend?: (message: string, attachments?: AttachmentPayload[]) => void;
  onSendMessage?: (message: string, attachments?: AttachmentPayload[]) => void;
  onStopStreaming?: () => void;
  isStreaming?: boolean;
  executionStatus?: ExecutionStatus;
  suggestedQuestions?: string[];  // 유지 (하위 호환성)
  onSuggestedQuestionClick?: (question: string) => void;  // 유지 (하위 호환성)
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  className?: string;
}

export const InputArea: React.FC<InputAreaProps> = ({
  onSend,
  onSendMessage,
  onStopStreaming,
  isStreaming = false,
  executionStatus,
  suggestedQuestions = [],
  onSuggestedQuestionClick,
  disabled = false,
  placeholder = '법률 관련 질문을 입력하세요...',
  maxLength = 10000,
  className,
}) => {
  const handleSendProp = onSendMessage || onSend;
  const [message, setMessage] = useState('');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);

  // 문서 첨부 메뉴 상태
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const [showDocumentPicker, setShowDocumentPicker] = useState(false);
  const [myDocuments, setMyDocuments] = useState<ExistingDocument[]>([]);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [documentSearchQuery, setDocumentSearchQuery] = useState('');

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const attachMenuRef = useRef<HTMLDivElement>(null);

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    const newHeight = Math.min(textarea.scrollHeight, 200);
    textarea.style.height = `${newHeight}px`;
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
  }, [message, adjustTextareaHeight]);

  useEffect(() => {
    if (attachments.length === 0 && attachmentError) {
      setAttachmentError(null);
    }
  }, [attachments.length, attachmentError]);

  // 메뉴 외부 클릭 시 닫기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (attachMenuRef.current && !attachMenuRef.current.contains(event.target as Node)) {
        setShowAttachMenu(false);
      }
    };

    if (showAttachMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showAttachMenu]);

  // 내 문서 목록 조회
  const loadMyDocuments = useCallback(async () => {
    setIsLoadingDocuments(true);
    try {
      const token = localStorage.getItem('lawlaw_auth_token');
      const response = await fetch('http://localhost:8000/api/v1/documents/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('문서 목록을 불러오는데 실패했습니다.');
      }

      const data = await response.json();
      setMyDocuments(data.results || data || []);
    } catch (error) {
      console.error('Failed to load documents:', error);
      setMyDocuments([]);
    } finally {
      setIsLoadingDocuments(false);
    }
  }, []);

  // 내 문서 보기 클릭
  const handleShowMyDocuments = useCallback(() => {
    setShowAttachMenu(false);
    setShowDocumentPicker(true);
    loadMyDocuments();
  }, [loadMyDocuments]);

  // 새 문서 첨부 클릭
  const handleNewDocumentClick = useCallback(() => {
    setShowAttachMenu(false);
    fileInputRef.current?.click();
  }, []);

  // 기존 문서 선택
  const handleSelectExistingDocument = useCallback(async (doc: ExistingDocument) => {
    setShowDocumentPicker(false);

    const id = `existing-${doc.id}-${Date.now()}`;

    // 첨부 목록에 추가 (로딩 상태)
    setAttachments((prev) => [
      ...prev,
      {
        id,
        documentId: doc.id,
        name: doc.title,
        size: doc.file_size || 0,
        type: doc.doc_type,
        status: 'processing',
        isExistingDocument: true,
      },
    ]);

    try {
      // 기존 문서의 내용 조회
      const token = localStorage.getItem('lawlaw_auth_token');
      const response = await fetch(`http://localhost:8000/api/v1/documents/${doc.id}/chunks/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('문서 내용을 불러오는데 실패했습니다.');
      }

      const data = await response.json();
      // 백엔드 응답: { document_id, chunk_count, chunks: [...] }
      const chunks = data.chunks || data.results || data || [];
      const content = chunks
        .map((chunk: any) => chunk.text)
        .join('\n\n');

      setAttachments((prev) =>
        prev.map((attachment) =>
          attachment.id === id
            ? {
                ...attachment,
                status: 'ready',
                processed: {
                  content: content || '(내용 없음)',
                  docType: doc.doc_type,
                  metadata: {
                    document_id: doc.id,
                    title: doc.title,
                    is_existing: true,
                  },
                },
              }
            : attachment
        )
      );
    } catch (error) {
      console.error('Failed to load document content:', error);
      setAttachments((prev) =>
        prev.map((attachment) =>
          attachment.id === id
            ? {
                ...attachment,
                status: 'error',
                error: '문서 내용을 불러오는데 실패했습니다.',
              }
            : attachment
        )
      );
    }
  }, []);

  // 문서 검색 필터링
  const filteredDocuments = myDocuments.filter((doc) =>
    doc.title.toLowerCase().includes(documentSearchQuery.toLowerCase())
  );

  // Handle send
  const handleSend = useCallback(() => {
    if (!message.trim() && attachments.length === 0) return;
    if (disabled || isStreaming) return;

    const pendingAttachment = attachments.find((a) => a.status === 'processing');
    if (pendingAttachment) {
      setAttachmentError('문서 전처리가 완료될 때까지 잠시 기다려 주세요.');
      return;
    }

    const erroredAttachment = attachments.find((a) => a.status === 'error');
    if (erroredAttachment) {
      setAttachmentError('오류가 발생한 첨부 파일을 제거하거나 다시 업로드해 주세요.');
      return;
    }

    const preparedAttachments: AttachmentPayload[] | undefined = attachments.length
      ? attachments
          .filter((a) => a.processed?.content)
          .map((a) => ({
            type: 'document',
            filename: a.name,
            mime_type: a.type,
            size: a.size,
            doc_type: a.processed?.docType,
            content: a.processed?.content,
            metadata: a.processed?.metadata,
          }))
      : undefined;

    handleSendProp?.(
      message.trim(),
      preparedAttachments
    );

    setMessage('');
    setAttachments([]);
    setAttachmentError(null);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [message, attachments, disabled, isStreaming, handleSendProp]);

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Handle file selection
  const preprocessAttachment = useCallback(async (id: string, file: File) => {
    try {
      const response = await agentHubService.attachments.preprocess(file);
      if (!response.success || !response.text) {
        throw new Error('문서 전처리에 실패했습니다. 다른 파일을 시도해 주세요.');
      }
      setAttachments((prev) => prev.map((attachment) =>
        attachment.id === id
          ? {
              ...attachment,
              status: 'ready',
              processed: {
                content: response.text || '',
                docType: response.metadata?.doc_type || response.file_type,
                metadata: response.metadata,
              },
              error: undefined,
            }
          : attachment
      ));
    } catch (err) {
      setAttachments((prev) => prev.map((attachment) =>
        attachment.id === id
          ? {
              ...attachment,
              status: 'error',
              error: err instanceof Error ? err.message : '전처리 실패',
            }
          : attachment
      ));
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    files.forEach((file) => {
      const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      setAttachments((prev) => [
        ...prev,
        {
          id,
          file,
          name: file.name,
          size: file.size,
          type: file.type,
          status: 'processing',
        },
      ]);
      preprocessAttachment(id, file);
    });

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Remove attachment
  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const canSend =
    (message.trim().length > 0 || attachments.length > 0) &&
    !disabled &&
    !isStreaming &&
    attachments.every((attachment) => attachment.status !== 'processing');

  return (
    <div className={cn('agent-hub-input', className)}>
      <div className="agent-hub-input__container">
        {/* Execution Status with Progress Indicator */}
        {executionStatus && (
          <div className="agent-hub-input__status-wrapper">
            {executionStatus.step ? (
              /* 새로운 Progress 이벤트가 있는 경우 ProgressIndicator 사용 */
              <div className="agent-hub-input__progress-container">
                <ProgressIndicator
                  progress={{
                    step: executionStatus.step,
                    percentage: executionStatus.progress ?? 0,
                    message: executionStatus.message || executionStatus.name,
                    execution_path: executionStatus.execution_path,
                    step_details: executionStatus.step_details,
                  }}
                  compact={false}
                  toolExecutions={executionStatus.toolExecutions}
                />
                {onStopStreaming && (
                  <button
                    onClick={onStopStreaming}
                    className="agent-hub-input__stop-btn agent-hub-input__stop-btn--progress"
                  >
                    중지
                  </button>
                )}
              </div>
            ) : (
              /* 레거시: 기존 심플 상태 표시 */
              <div className="agent-hub-input__status">
                <div className="agent-hub-input__status-content">
                  <LoadingSpinner />
                  <span>{executionStatus.name}</span>
                  {executionStatus.progress !== undefined && (
                    <span className="agent-hub-input__status-progress">
                      {executionStatus.progress}%
                    </span>
                  )}
                </div>
                {onStopStreaming && (
                  <button
                    onClick={onStopStreaming}
                    className="agent-hub-input__stop-btn"
                  >
                    중지
                  </button>
                )}
              </div>
            )}
          </div>
        )}


        {/* Attachments Preview */}
        {attachments.length > 0 && (
          <div className="agent-hub-input__attachments">
            {attachments.map((attachment) => (
              <div key={attachment.id} className="agent-hub-input__attachment">
                <FileIcon />
                <div className="agent-hub-input__attachment-info">
                  <span className="agent-hub-input__attachment-name">
                    {attachment.name}
                  </span>
                  <span className="agent-hub-input__attachment-size">
                    {formatFileSize(attachment.size)}
                  </span>
                  <span className={cn(
                    'agent-hub-input__attachment-status',
                    attachment.status === 'error' && 'agent-hub-input__attachment-status--error'
                  )}>
                    {attachment.status === 'processing' && '전처리 중...'}
                    {attachment.status === 'ready' && '준비 완료'}
                    {attachment.status === 'error' && (attachment.error || '처리 실패')}
                  </span>
                </div>
                <button
                  onClick={() => removeAttachment(attachment.id)}
                  className="agent-hub-input__attachment-remove"
                >
                  <CloseIcon />
                </button>
              </div>
            ))}
            {attachmentError && (
              <div className="agent-hub-input__attachment-error">
                {attachmentError}
              </div>
            )}
          </div>
        )}

        {/* Input Box */}
        <div
          className={cn(
            'agent-hub-input__box',
            isFocused && 'agent-hub-input__box--focused',
            disabled && 'agent-hub-input__box--disabled'
          )}
        >
          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value.slice(0, maxLength))}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="agent-hub-input__textarea"
          />

          {/* Actions */}
          <div className="agent-hub-input__actions">
            {/* Attachment Button with Menu */}
            <div className="agent-hub-input__attach-wrapper" ref={attachMenuRef}>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                className="agent-hub-input__file-input"
                accept=".pdf,.doc,.docx,.txt,.hwp,.jpg,.jpeg,.png"
              />
              <button
                onClick={() => setShowAttachMenu(!showAttachMenu)}
                disabled={disabled}
                className="agent-hub-input__action-btn"
                title="문서 첨부"
              >
                <AttachmentIcon />
              </button>

              {/* Attachment Menu */}
              {showAttachMenu && (
                <div className="agent-hub-input__attach-menu">
                  <button
                    className="agent-hub-input__attach-menu-item"
                    onClick={handleShowMyDocuments}
                  >
                    <FolderIcon />
                    <span>내 문서 보기</span>
                  </button>
                  <button
                    className="agent-hub-input__attach-menu-item"
                    onClick={handleNewDocumentClick}
                  >
                    <UploadIcon />
                    <span>새 문서 첨부</span>
                  </button>
                </div>
              )}
            </div>

            {/* Send Button */}
            <button
              onClick={handleSend}
              disabled={!canSend}
              className={cn(
                'agent-hub-input__send-btn',
                canSend && 'agent-hub-input__send-btn--active'
              )}
              title="전송"
            >
              <SendIcon />
            </button>
          </div>
        </div>

        {/* Document Picker Modal */}
        {showDocumentPicker && (
          <div className="agent-hub-input__doc-picker-overlay">
            <div className="agent-hub-input__doc-picker">
              <div className="agent-hub-input__doc-picker-header">
                <h3>내 문서 선택</h3>
                <button
                  className="agent-hub-input__doc-picker-close"
                  onClick={() => setShowDocumentPicker(false)}
                >
                  <CloseIcon />
                </button>
              </div>

              <div className="agent-hub-input__doc-picker-search">
                <SearchIcon />
                <input
                  type="text"
                  placeholder="문서 검색..."
                  value={documentSearchQuery}
                  onChange={(e) => setDocumentSearchQuery(e.target.value)}
                />
              </div>

              <div className="agent-hub-input__doc-picker-list">
                {isLoadingDocuments ? (
                  <div className="agent-hub-input__doc-picker-loading">
                    <LoadingSpinner />
                    <span>문서 목록을 불러오는 중...</span>
                  </div>
                ) : filteredDocuments.length === 0 ? (
                  <div className="agent-hub-input__doc-picker-empty">
                    {myDocuments.length === 0
                      ? '저장된 문서가 없습니다.'
                      : '검색 결과가 없습니다.'}
                  </div>
                ) : (
                  filteredDocuments.map((doc) => (
                    <button
                      key={doc.id}
                      className="agent-hub-input__doc-picker-item"
                      onClick={() => handleSelectExistingDocument(doc)}
                    >
                      <FileIcon />
                      <div className="agent-hub-input__doc-picker-item-info">
                        <span className="agent-hub-input__doc-picker-item-title">
                          {doc.title}
                        </span>
                        <span className="agent-hub-input__doc-picker-item-meta">
                          {doc.doc_type} · {new Date(doc.created_at).toLocaleDateString('ko-KR')}
                        </span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* Helper Text */}
        <div className="agent-hub-input__helper">
          <span>
            <kbd>Enter</kbd> 전송 · <kbd>Shift + Enter</kbd> 줄바꿈
          </span>
          <span>{message.length.toLocaleString()} / {maxLength.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
};

// Icons
const AttachmentIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const SendIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="22" y1="2" x2="11" y2="13" strokeLinecap="round" strokeLinejoin="round" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const FileIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeLinecap="round" strokeLinejoin="round" />
    <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const CloseIcon: React.FC = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18" strokeLinecap="round" strokeLinejoin="round" />
    <line x1="6" y1="6" x2="18" y2="18" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const LoadingSpinner: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="agent-hub-input__spinner">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25" />
    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
  </svg>
);

const FolderIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const UploadIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" strokeLinecap="round" strokeLinejoin="round" />
    <polyline points="17 8 12 3 7 8" strokeLinecap="round" strokeLinejoin="round" />
    <line x1="12" y1="3" x2="12" y2="15" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const SearchIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8" strokeLinecap="round" strokeLinejoin="round" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export default InputArea;
