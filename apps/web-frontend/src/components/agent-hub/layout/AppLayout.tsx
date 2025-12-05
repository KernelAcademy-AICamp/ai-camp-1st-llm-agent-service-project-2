/**
 * Agent Hub - App Layout (LawLawKR Style)
 *
 * 2컬럼 레이아웃: LawLawKR 스타일 사이드바 + 메인 채팅 영역
 * 기존 서비스 스타일과 완전히 통합
 */

import React, { useState, useCallback } from 'react';
import { cn } from '../../../lib/utils';
import { useIsMobile, useIsDesktop } from '../../../hooks';
import Sidebar from './Sidebar';
import InputArea from './InputArea';
import type { AttachmentPayload } from '../../../types/agentHub';
import type { ToolExecutionEvent } from '../../../services/agentHubService';

// 세션 타입
export interface SessionItem {
  id: string;
  title: string;
  lastMessage?: string;
  timestamp: Date;
  isActive?: boolean;
}

// 실행 상태 타입
export interface ExecutionStatus {
  name: string;
  progress?: number;
  // Progress 이벤트 확장 필드
  step?: 'ANALYZING' | 'PLANNING' | 'SEARCHING' | 'EXECUTING' | 'THINKING' | 'GENERATING' | 'COMPLETED';
  message?: string;
  execution_path?: 'fast' | 'medium' | 'deep' | 'thinking';
  step_details?: Record<string, any>;
  // 도구 실행 로그 (Phase 7)
  toolExecutions?: ToolExecutionEvent[];
}

interface AppLayoutProps {
  children: React.ReactNode;
  className?: string;
  // 세션 관련
  sessions?: SessionItem[];
  currentSessionId?: string | null;
  onNewChat?: () => void;
  onSelectSession?: (id: string) => void;
  onDeleteSession?: (id: string) => void;
  // 메시지 관련
  onSendMessage?: (message: string, attachments?: AttachmentPayload[]) => void;
  onStopStreaming?: () => void;
  isStreaming?: boolean;
  executionStatus?: ExecutionStatus;
  // 추천 질문
  suggestedQuestions?: string[];
  onSuggestedQuestionClick?: (question: string) => void;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  className,
  sessions = [],
  currentSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onSendMessage,
  onStopStreaming,
  isStreaming = false,
  executionStatus,
  suggestedQuestions = [],
  onSuggestedQuestionClick,
}) => {
  const isMobile = useIsMobile();
  const isDesktop = useIsDesktop();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const toggleSidebar = useCallback(() => {
    if (isMobile) {
      setMobileSidebarOpen((prev) => !prev);
    } else {
      setSidebarCollapsed((prev) => !prev);
    }
  }, [isMobile]);

  const closeMobileSidebar = useCallback(() => {
    setMobileSidebarOpen(false);
  }, []);

  return (
    <div
      className={cn('agent-hub-layout', className)}
      data-testid="agent-hub-layout"
    >
      {/* Sidebar - LawLawKR Style */}
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onNewChat={onNewChat}
        onSelectSession={onSelectSession}
        onDeleteSession={onDeleteSession}
        collapsed={isDesktop ? sidebarCollapsed : false}
        onToggle={toggleSidebar}
      />

      {/* Mobile Overlay */}
      {!isDesktop && mobileSidebarOpen && (
        <div
          className="agent-hub-overlay"
          onClick={closeMobileSidebar}
          aria-hidden="true"
        />
      )}

      {/* Main Content */}
      <main className="agent-hub-main">
        {/* Header */}
        <header className="agent-hub-header">
          <div className="agent-hub-header__left">
            <button
              className="agent-hub-header__menu-btn"
              onClick={toggleSidebar}
              aria-label="사이드바 토글"
            >
              <MenuIcon />
            </button>
            <h1 className="agent-hub-header__title">법률 AI 어시스턴트</h1>
          </div>
          <div className="agent-hub-header__right">
            <button className="agent-hub-header__action-btn" title="설정">
              <SettingsIcon />
            </button>
          </div>
        </header>

        {/* Chat Area */}
        <div className="agent-hub-chat">
          <div className="agent-hub-chat__messages">
            {children}
          </div>

          {/* Input Area */}
          <div className="agent-hub-chat__input">
            <InputArea
              onSendMessage={onSendMessage}
              onStopStreaming={onStopStreaming}
              isStreaming={isStreaming}
              executionStatus={executionStatus}
              suggestedQuestions={suggestedQuestions}
              onSuggestedQuestionClick={onSuggestedQuestionClick}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

// Icons
const MenuIcon: React.FC = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M3 12h18M3 6h18M3 18h18" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const SettingsIcon: React.FC = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
);

export default AppLayout;
