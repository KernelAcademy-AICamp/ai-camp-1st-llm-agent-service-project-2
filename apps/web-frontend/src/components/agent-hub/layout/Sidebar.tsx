/**
 * Agent Hub - Sidebar Component (ChatGPT Style)
 *
 * 새 대화 버튼, 최근 대화 목록, 접이식 지원
 * 기존 서비스 스타일과 일관성 유지
 */

import React, { useState } from 'react';
import { cn, formatRelativeDate, truncate } from '../../../lib/utils';
import { SessionItem } from './AppLayout';

interface Conversation {
  id: string;
  title: string | null;
  preview: string;
  updatedAt: Date;
  projectId?: string;
}

interface SidebarProps {
  sessions?: SessionItem[];
  currentSessionId?: string | null;
  onNewChat?: () => void;
  onSelectSession?: (id: string) => void;
  onDeleteSession?: (id: string) => void;
  collapsed?: boolean;
  onToggle?: () => void;
  className?: string;
}

// Mock data 제거 - API 실패 시 로컬 스토리지 세션이 표시됨

export const Sidebar: React.FC<SidebarProps> = ({
  sessions = [],
  currentSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  collapsed = false,
  onToggle,
  className,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  // sessions -> conversations 변환
  const conversations: Conversation[] = sessions.map((s) => ({
    id: s.id,
    title: s.title,
    preview: s.lastMessage || '',
    updatedAt: s.timestamp,
  }));

  const filteredConversations = conversations.filter((conv) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    const title = conv.title?.toLowerCase() ?? '';
    return (
      title.includes(query) ||
      conv.preview.toLowerCase().includes(query)
    );
  });

  // 접힌 상태일 때
  if (collapsed) {
    return (
      <div className={cn('agent-hub-sidebar__collapsed', className)}>
        <button
          className="agent-hub-sidebar__toggle-btn"
          onClick={onToggle}
          title="사이드바 열기"
        >
          <ChevronRightIcon />
        </button>
        <button
          className="agent-hub-sidebar__new-btn-mini"
          onClick={onNewChat}
          title="새 대화"
        >
          <PlusIcon />
        </button>
      </div>
    );
  }

  return (
    <div className={cn('agent-hub-sidebar__content', className)}>
      {/* Header */}
      <div className="agent-hub-sidebar__header">
        <button
          className="agent-hub-sidebar__toggle-btn"
          onClick={onToggle}
          title="사이드바 접기"
        >
          <ChevronLeftIcon />
        </button>
        <span className="agent-hub-sidebar__logo">Legal AI</span>
      </div>

      {/* New Chat Button */}
      <div className="agent-hub-sidebar__new-chat">
        <button
          className="agent-hub-sidebar__new-btn"
          onClick={onNewChat}
        >
          <PlusIcon />
          <span>새 대화</span>
        </button>
      </div>

      {/* Search */}
      <div className="agent-hub-sidebar__search">
        <SearchIcon />
        <input
          type="text"
          placeholder="대화 검색..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Conversations List */}
      <div className="agent-hub-sidebar__list">
        <div className="agent-hub-sidebar__list-header">
          <span>최근 대화</span>
        </div>

        {filteredConversations.length > 0 ? (
          <ul className="agent-hub-sidebar__conversations">
            {filteredConversations.map((conv) => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isActive={conv.id === currentSessionId}
                onClick={() => onSelectSession?.(conv.id)}
                onDelete={() => onDeleteSession?.(conv.id)}
              />
            ))}
          </ul>
        ) : (
          <div className="agent-hub-sidebar__empty">
            <p>{searchQuery ? '검색 결과가 없습니다' : '대화 내역이 없습니다'}</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="agent-hub-sidebar__footer">
        <button className="agent-hub-sidebar__footer-btn">
          <HelpIcon />
          <span>도움말</span>
        </button>
      </div>
    </div>
  );
};

// Conversation Item Component
interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onClick: () => void;
  onDelete?: () => void;
}

const ConversationItem: React.FC<ConversationItemProps> = ({
  conversation,
  isActive,
  onClick,
  onDelete,
}) => {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <li
      className={cn(
        'agent-hub-sidebar__item',
        isActive && 'agent-hub-sidebar__item--active'
      )}
    >
      <button
        className="agent-hub-sidebar__item-btn"
        onClick={onClick}
      >
        <ChatIcon />
        <div className="agent-hub-sidebar__item-content">
          <span className="agent-hub-sidebar__item-title">
            {truncate(conversation.title ?? '제목 없음', 25)}
          </span>
          <span className="agent-hub-sidebar__item-time">
            {formatRelativeDate(conversation.updatedAt)}
          </span>
        </div>
      </button>

      <div className="agent-hub-sidebar__item-actions">
        <button
          className="agent-hub-sidebar__item-menu"
          onClick={(e) => {
            e.stopPropagation();
            setShowMenu(!showMenu);
          }}
        >
          <MoreIcon />
        </button>

        {showMenu && (
          <div className="agent-hub-sidebar__dropdown">
            <button onClick={onDelete}>
              <TrashIcon />
              삭제
            </button>
          </div>
        )}
      </div>
    </li>
  );
};

// Icons
const PlusIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 5v14M5 12h14" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const SearchIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8" />
    <path d="M21 21l-4.35-4.35" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const ChatIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const MoreIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="1" />
    <circle cx="19" cy="12" r="1" />
    <circle cx="5" cy="12" r="1" />
  </svg>
);

const TrashIcon: React.FC = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="3 6 5 6 21 6" />
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
  </svg>
);

const ChevronLeftIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="15 18 9 12 15 6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const ChevronRightIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="9 18 15 12 9 6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const HelpIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10" />
    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" strokeLinecap="round" strokeLinejoin="round" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

export default Sidebar;
