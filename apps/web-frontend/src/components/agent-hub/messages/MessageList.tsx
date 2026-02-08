/**
 * Agent Hub - Message List Component (ChatGPT Style)
 *
 * 메시지 목록을 표시하고 자동 스크롤 처리
 * 깔끔한 중앙 정렬 레이아웃
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { cn } from '../../../lib/utils';
import { MessageCard, Message } from './MessageCard';

interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
  className?: string;
  sessionId?: string;
  onRetry?: (messageId: string) => void;
  onSuggestedQuestionClick?: (question: string) => void;
  onSaveAnalysis?: (message: Message) => Promise<{ success: boolean; document_url?: string; error?: string }>;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading = false,
  className,
  sessionId,
  onRetry,
  onSuggestedQuestionClick,
  onSaveAnalysis,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [isAutoScrolling, setIsAutoScrolling] = useState(true);

  // Scroll to bottom
  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    bottomRef.current?.scrollIntoView({ behavior });
  }, []);

  // Handle scroll events
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;

    setIsAutoScrolling(isNearBottom);
    setShowScrollButton(!isNearBottom && messages.length > 3);
  }, [messages.length]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (isAutoScrolling && messages.length > 0) {
      scrollToBottom();
    }
  }, [messages, isAutoScrolling, scrollToBottom]);

  // Initial scroll to bottom
  useEffect(() => {
    scrollToBottom('auto');
  }, [scrollToBottom]);

  if (messages.length === 0 && !isLoading) {
    return <EmptyState onSuggestedQuestionClick={onSuggestedQuestionClick} />;
  }

  return (
    <div className={cn('agent-hub-message-list', className)}>
      {/* Messages Container */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="agent-hub-message-list__container"
      >
        <div className="agent-hub-message-list__content">
          {messages.map((message, index) => (
            <MessageCard
              key={message.id}
              message={message}
              showAvatar={shouldShowAvatar(messages, index)}
              sessionId={sessionId}
              onSaveAnalysis={onSaveAnalysis}
            />
          ))}

          {/* Scroll anchor */}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <button
          onClick={() => scrollToBottom()}
          className="agent-hub-message-list__scroll-btn"
          aria-label="최신 메시지로 스크롤"
        >
          <ChevronDownIcon />
        </button>
      )}
    </div>
  );
};

/**
 * Empty State Component
 */
interface EmptyStateProps {
  onSuggestedQuestionClick?: (question: string) => void;
}

const SUGGESTED_QUESTIONS = [
  '근로계약 해지 시 주의사항이 무엇인가요?',
  '부동산 매매 계약서 검토 요청',
  '손해배상 청구 요건에 대해 알려주세요',
];

const EmptyState: React.FC<EmptyStateProps> = ({ onSuggestedQuestionClick }) => {
  return (
    <div className="agent-hub-empty">
      <div className="agent-hub-empty__icon">
        <ChatBubbleIcon />
      </div>
      <h3 className="agent-hub-empty__title">새로운 대화 시작</h3>
      <p className="agent-hub-empty__description">
        법률 관련 질문이나 사건 분석을 요청해보세요.
        AI가 관련 판례와 법령을 검토하여 답변해드립니다.
      </p>
      <div className="agent-hub-empty__suggestions">
        {SUGGESTED_QUESTIONS.map((question, index) => (
          <button
            key={index}
            className="agent-hub-empty__suggestion"
            onClick={() => onSuggestedQuestionClick?.(question)}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
};

// Utility function
function shouldShowAvatar(messages: Message[], index: number): boolean {
  if (index === 0) return true;
  return messages[index].role !== messages[index - 1].role;
}

// Icons
const ChevronDownIcon: React.FC = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="6 9 12 15 18 9" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const ChatBubbleIcon: React.FC = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export default MessageList;
