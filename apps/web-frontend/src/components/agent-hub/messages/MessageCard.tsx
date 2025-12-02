/**
 * Agent Hub - Message Card Component (ChatGPT Style)
 *
 * AI/User 메시지를 구분하여 표시
 * 깔끔한 카드 스타일
 */

import React, { useState } from 'react';
import { cn, formatTime, copyToClipboard } from '../../../lib/utils';
import { MarkdownRenderer } from './MarkdownRenderer';
import { TypingIndicator } from './TypingIndicator';
import SourceDetailModal from '../../SourceDetailModal/SourceDetailModal';
import type { MessageMetadata, DocumentAnalysisMetadata, MessageSource } from '../../../types/agentHub';

// Re-export SourceItem as alias for MessageSource for backward compatibility
export type SourceItem = MessageSource;

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: MessageMetadata;
  isStreaming?: boolean;
}

interface MessageCardProps {
  message: Message;
  showAvatar?: boolean;
  className?: string;
  sessionId?: string;
  onSaveAnalysis?: (message: Message) => Promise<{ success: boolean; document_url?: string; error?: string }>;
}

// Icons - 컴포넌트보다 먼저 정의해야 사용 가능
const UserIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="12" cy="7" r="4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const BotIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="11" width="18" height="10" rx="2" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="12" cy="5" r="2" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M12 7v4" strokeLinecap="round" strokeLinejoin="round" />
    <line x1="8" y1="16" x2="8" y2="16" strokeLinecap="round" strokeLinejoin="round" />
    <line x1="16" y1="16" x2="16" y2="16" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const CopyIcon: React.FC = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const CheckIcon: React.FC = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="20 6 9 17 4 12" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const SaveIcon: React.FC = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" strokeLinecap="round" strokeLinejoin="round" />
    <polyline points="17 21 17 13 7 13 7 21" strokeLinecap="round" strokeLinejoin="round" />
    <polyline points="7 3 7 8 15 8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const LoadingSpinner: React.FC = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin">
    <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
    <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
  </svg>
);

const SourceIcon: React.FC = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeLinecap="round" strokeLinejoin="round" />
    <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round" />
    <line x1="16" y1="13" x2="8" y2="13" strokeLinecap="round" strokeLinejoin="round" />
    <line x1="16" y1="17" x2="8" y2="17" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const BookIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const ChevronIcon: React.FC<{ direction: 'up' | 'down' }> = ({ direction }) => (
  <svg
    width="12"
    height="12"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    style={{ transform: direction === 'up' ? 'rotate(180deg)' : 'none' }}
  >
    <polyline points="6 9 12 15 18 9" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const MessageCard: React.FC<MessageCardProps> = ({
  message,
  showAvatar = true,
  className,
  sessionId,
  onSaveAnalysis,
}) => {
  const [copied, setCopied] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [savedDocumentUrl, setSavedDocumentUrl] = useState<string | null>(null);

  const isUser = message.role === 'user';
  const isStreaming = message.isStreaming;
  const hasDocumentAnalysis = message.metadata?.documentAnalysis != null;
  // 기존 문서면 저장 버튼 표시하지 않음 (이미 저장된 문서)
  const isExistingDocument = message.metadata?.documentAnalysis?.is_existing === true;
  const canSaveAnalysis = hasDocumentAnalysis && !isExistingDocument;

  const handleCopy = async () => {
    const success = await copyToClipboard(message.content);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSaveAnalysis = async () => {
    if (!onSaveAnalysis || isSaving || saveStatus === 'success') return;

    setIsSaving(true);
    setSaveStatus('idle');

    try {
      const result = await onSaveAnalysis(message);
      if (result.success) {
        setSaveStatus('success');
        setSavedDocumentUrl(result.document_url || null);
        // 3초 후 상태 초기화 (URL은 유지)
        setTimeout(() => setSaveStatus('idle'), 3000);
      } else {
        setSaveStatus('error');
        console.error('Save failed:', result.error);
        setTimeout(() => setSaveStatus('idle'), 3000);
      }
    } catch (error) {
      console.error('Save error:', error);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      className={cn(
        'agent-hub-msg',
        isUser ? 'agent-hub-msg--user' : 'agent-hub-msg--assistant',
        className
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Avatar */}
      {showAvatar && (
        <div className={cn(
          'agent-hub-msg__avatar',
          isUser ? 'agent-hub-msg__avatar--user' : 'agent-hub-msg__avatar--assistant'
        )}>
          {isUser ? <UserIcon /> : <BotIcon />}
        </div>
      )}

      {/* Content */}
      <div className="agent-hub-msg__content">
        {/* Header */}
        <div className="agent-hub-msg__header">
          <span className="agent-hub-msg__name">
            {isUser ? '나' : 'AI 어시스턴트'}
          </span>
          <span className="agent-hub-msg__time">
            {formatTime(message.timestamp)}
          </span>
        </div>

        {/* Bubble */}
        <div className={cn(
          'agent-hub-msg__bubble',
          isUser ? 'agent-hub-msg__bubble--user' : 'agent-hub-msg__bubble--assistant'
        )}>
          {isStreaming ? (
            <TypingIndicator />
          ) : isUser ? (
            <p className="agent-hub-msg__text">{message.content}</p>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}
        </div>

        {/* Actions */}
        {!isUser && !isStreaming && (
          <div className={cn(
            'agent-hub-msg__actions',
            showActions && 'agent-hub-msg__actions--visible'
          )}>
            <button onClick={handleCopy} className="agent-hub-msg__action-btn">
              {copied ? <CheckIcon /> : <CopyIcon />}
              <span>{copied ? '복사됨' : '복사'}</span>
            </button>

            {/* 새 문서 분석이 있을 때만 저장 버튼 표시 (기존 문서는 이미 저장됨) */}
            {canSaveAnalysis && onSaveAnalysis && (
              <>
                <button
                  onClick={handleSaveAnalysis}
                  disabled={isSaving || saveStatus === 'success'}
                  className={cn(
                    'agent-hub-msg__action-btn',
                    'agent-hub-msg__action-btn--save',
                    saveStatus === 'success' && 'agent-hub-msg__action-btn--success',
                    saveStatus === 'error' && 'agent-hub-msg__action-btn--error'
                  )}
                >
                  {isSaving ? (
                    <>
                      <LoadingSpinner />
                      <span>저장 중...</span>
                    </>
                  ) : saveStatus === 'success' ? (
                    <>
                      <CheckIcon />
                      <span>저장됨</span>
                    </>
                  ) : saveStatus === 'error' ? (
                    <>
                      <SaveIcon />
                      <span>실패</span>
                    </>
                  ) : (
                    <>
                      <SaveIcon />
                      <span>문서함에 저장</span>
                    </>
                  )}
                </button>
                {savedDocumentUrl && (
                  <a
                    href={savedDocumentUrl}
                    className="agent-hub-msg__action-btn agent-hub-msg__action-btn--link"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <span>문서 보기</span>
                  </a>
                )}
              </>
            )}
          </div>
        )}

        {/* Metadata */}
        {!isUser && message.metadata && !isStreaming && (
          <MessageMetadataView metadata={message.metadata} />
        )}
      </div>
    </div>
  );
};

// Message Metadata Component
interface MessageMetadataViewProps {
  metadata: MessageMetadata;
}

const MessageMetadataView: React.FC<MessageMetadataViewProps> = ({ metadata }) => {
  const [showSources, setShowSources] = useState(false);
  const [selectedSource, setSelectedSource] = useState<MessageSource | null>(null);
  const [isSourceModalOpen, setIsSourceModalOpen] = useState(false);

  // Source card click handler
  const handleSourceClick = (source: MessageSource) => {
    setSelectedSource(source);
    setIsSourceModalOpen(true);
  };

  const handleCloseSourceModal = () => {
    setIsSourceModalOpen(false);
    setSelectedSource(null);
  };

  // Convert MessageSource to SourceDetailModal format
  const convertToModalFormat = (source: MessageSource | null) => {
    if (!source) return null;
    return {
      title: source.title || source.case_number,
      case_number: source.case_number,
      court: source.court,
      date: source.date,
      doc_type: source.doc_type,
      text_snippet: source.content || source.snippet,
      relevance_score: source.score || source.relevanceScore,
      source: source.source,
    };
  };

  const hasMetadata =
    metadata.workflows?.length ||
    metadata.executionTime ||
    metadata.sources?.length ||
    metadata.tokensUsed ||
    metadata.documentAnalysis;

  if (!hasMetadata) return null;

  // Score 관련도 라벨
  const getScoreLabel = (score: number, rank: number): string => {
    if (rank === 1) return '최고 관련';
    if (rank <= 3) return '높은 관련';
    if (rank <= 5) return '관련';
    return '일부 관련';
  };

  const getScoreClass = (score: number): string => {
    if (score >= 0.010) return 'score-high';
    if (score >= 0.005) return 'score-medium';
    return 'score-low';
  };

  return (
    <div className="agent-hub-msg__metadata">
      <div className="agent-hub-msg__metadata-row">
        {metadata.workflows?.map((workflow, idx) => (
          <span key={idx} className="agent-hub-msg__tag">
            {workflow}
          </span>
        ))}
        {metadata.executionTime && (
          <span className="agent-hub-msg__meta-item">
            {metadata.executionTime.toFixed(1)}s
          </span>
        )}
        {metadata.sources && metadata.sources.length > 0 && (
          <button
            className="agent-hub-msg__sources-toggle"
            onClick={() => setShowSources(!showSources)}
          >
            <SourceIcon />
            {metadata.sources.length}개 참고자료
            <ChevronIcon direction={showSources ? 'up' : 'down'} />
          </button>
        )}
      </div>

      {/* Sources List - LegalResearch 스타일 */}
      {showSources && metadata.sources && metadata.sources.length > 0 && (
        <div className="agent-hub-msg__sources">
          <div className="agent-hub-msg__sources-header">
            <h4>참고 자료 ({metadata.sources.length}건)</h4>
            <span className="agent-hub-msg__sources-description">
              RAG 검색으로 찾은 관련 문서
            </span>
          </div>
          <div className="agent-hub-msg__sources-list">
            {metadata.sources.map((source, idx) => (
              <div
                key={idx}
                className={`agent-hub-msg__source-card ${getScoreClass(source.score || 0)} agent-hub-msg__source-card--clickable`}
                onClick={() => handleSourceClick(source)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && handleSourceClick(source)}
              >
                <div className="agent-hub-msg__source-header">
                  <span className="agent-hub-msg__source-rank">#{idx + 1}</span>
                  <div className="agent-hub-msg__source-title-wrap">
                    <BookIcon />
                    <h5 className="agent-hub-msg__source-title">
                      {source.url ? (
                        <a href={source.url} target="_blank" rel="noopener noreferrer">
                          {source.title || source.case_number || '출처 없음'}
                        </a>
                      ) : (
                        source.title || source.case_number || '출처 없음'
                      )}
                    </h5>
                  </div>
                  <div className="agent-hub-msg__source-badges">
                    {source.doc_type && (
                      <span className="agent-hub-msg__source-type">{source.doc_type}</span>
                    )}
                    {source.score !== undefined && source.score > 0 && (
                      <span className={`agent-hub-msg__source-score ${getScoreClass(source.score)}`}>
                        {getScoreLabel(source.score, idx + 1)}
                      </span>
                    )}
                  </div>
                </div>
                {source.content && (
                  <p className="agent-hub-msg__source-content">
                    {source.content.slice(0, 200)}
                    {source.content.length > 200 ? '...' : ''}
                  </p>
                )}
                <div className="agent-hub-msg__source-footer">
                  {source.court && (
                    <span className="agent-hub-msg__source-court">{source.court}</span>
                  )}
                  {source.date && (
                    <span className="agent-hub-msg__source-date">{source.date}</span>
                  )}
                  {source.case_number && (
                    <span className="agent-hub-msg__source-case">{source.case_number}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {metadata.documentAnalysis && (
        <DocumentAnalysisView analysis={metadata.documentAnalysis} />
      )}

      {/* Source Detail Modal */}
      <SourceDetailModal
        isOpen={isSourceModalOpen}
        onClose={handleCloseSourceModal}
        source={convertToModalFormat(selectedSource)}
      />
    </div>
  );
};

interface DocumentAnalysisViewProps {
  analysis: DocumentAnalysisMetadata;
}

const DocumentAnalysisView: React.FC<DocumentAnalysisViewProps> = ({ analysis }) => {
  const clauses = analysis.clauses?.slice(0, 5) || [];
  const risks = analysis.risks?.slice(0, 5) || [];

  return (
    <div className="agent-hub-doc-analysis">
      <div className="agent-hub-doc-analysis__section">
        <div className="agent-hub-doc-analysis__header">
          <span>문서 요약</span>
          {analysis.doc_type && (
            <span className="agent-hub-doc-analysis__badge">{analysis.doc_type}</span>
          )}
        </div>
        <p className="agent-hub-doc-analysis__summary">
          {analysis.summary || '요약 정보를 찾을 수 없습니다.'}
        </p>
      </div>

      {clauses.length > 0 && (
        <div className="agent-hub-doc-analysis__section">
          <div className="agent-hub-doc-analysis__header">
            <span>핵심 조항</span>
            <span className="agent-hub-doc-analysis__count">{clauses.length}개</span>
          </div>
          <ul className="agent-hub-doc-analysis__list">
            {clauses.map((clause, idx) => (
              <li key={idx}>
                <strong>{clause.clause_number || `조항 ${idx + 1}`}</strong>
                <p>{clause.text}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {risks.length > 0 && (
        <div className="agent-hub-doc-analysis__section">
          <div className="agent-hub-doc-analysis__header">
            <span>리스크 분석</span>
            {analysis.needs_expert_review && (
              <span className="agent-hub-doc-analysis__badge agent-hub-doc-analysis__badge--alert">
                전문가 검토 필요
              </span>
            )}
          </div>
          <ul className="agent-hub-doc-analysis__list agent-hub-doc-analysis__list--risk">
            {risks.map((risk, idx) => (
              <li key={idx}>
                <div className="agent-hub-doc-analysis__risk-row">
                  <strong>{risk.name || `리스크 ${idx + 1}`}</strong>
                  {risk.severity && (
                    <span
                      className={cn(
                        'agent-hub-doc-analysis__badge',
                        `severity-${risk.severity.toLowerCase()}`
                      )}
                    >
                      {risk.severity}
                    </span>
                  )}
                </div>
                <p>{risk.description}</p>
                {risk.recommendation && (
                  <p className="agent-hub-doc-analysis__recommendation">
                    권장 사항: {risk.recommendation}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default MessageCard;
