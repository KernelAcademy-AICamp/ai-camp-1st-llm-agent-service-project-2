/**
 * Agent Hub Sidebar - LawLawKR 스타일 통합
 *
 * 기존 LawLawKR 사이드바 스타일 유지
 * AI 어시스턴트 메뉴 + 최근 대화 목록 추가
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';
import {
  FiHome,
  FiFileText,
  FiSearch,
  FiBarChart2,
  FiUsers,
  FiSettings,
  FiChevronDown,
  FiChevronRight,
  FiChevronLeft,
  FiFile,
  FiAlertTriangle,
  FiLayers,
  FiBriefcase,
  FiGrid,
  FiLogOut,
  FiMenu,
  FiMessageSquare,
  FiPlus,
  FiTrash2,
  FiMoreHorizontal
} from 'react-icons/fi';

// Types
interface MenuItem {
  label: string;
  path: string;
  icon?: React.ReactNode;
}

interface MenuSection {
  id: string;
  title: string;
  icon: React.ReactNode;
  items?: MenuItem[];
  path?: string;
}

interface ChatSession {
  id: string;
  title: string;
  lastMessage?: string;
  timestamp: Date;
  isActive?: boolean;
}

interface AgentHubSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  sessions?: ChatSession[];
  currentSessionId?: string | null;
  onNewChat?: () => void;
  onSelectSession?: (id: string) => void;
  onDeleteSession?: (id: string) => void;
}

const AgentHubSidebar: React.FC<AgentHubSidebarProps> = ({
  collapsed,
  onToggle,
  sessions = [],
  currentSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAuthenticated } = useAuth();
  const [expandedSections, setExpandedSections] = useState<string[]>(['ai-assistant', 'documents']);
  const [showSessionMenu, setShowSessionMenu] = useState<string | null>(null);

  // Auto-expand section based on current path
  useEffect(() => {
    const currentPath = location.pathname;

    if (currentPath.startsWith('/agent-hub')) {
      setExpandedSections(prev => {
        if (!prev || !Array.isArray(prev)) return ['ai-assistant'];
        if (prev.includes('ai-assistant')) return prev;
        return [...prev, 'ai-assistant'];
      });
    }
    if (currentPath.startsWith('/documents') || currentPath.startsWith('/research')) {
      setExpandedSections(prev => {
        if (!prev || !Array.isArray(prev)) return ['documents'];
        if (prev.includes('documents')) return prev;
        return [...prev, 'documents'];
      });
    }
    if (currentPath.startsWith('/risk-dashboard') || currentPath.startsWith('/analysis')) {
      setExpandedSections(prev => {
        if (!prev || !Array.isArray(prev)) return ['analysis'];
        if (prev.includes('analysis')) return prev;
        return [...prev, 'analysis'];
      });
    }
  }, [location.pathname]);

  const menuSections: MenuSection[] = [
    {
      id: 'dashboard',
      title: '대시보드',
      icon: <FiHome />,
      path: '/app'
    },
    {
      id: 'ai-assistant',
      title: 'AI 어시스턴트',
      icon: <FiMessageSquare />,
      path: '/agent-hub'
    },
    {
      id: 'documents',
      title: '문서',
      icon: <FiFileText />,
      items: [
        { label: '문서 관리', path: '/documents', icon: <FiFile /> },
        { label: '법률 리서치', path: '/research', icon: <FiSearch /> }
      ]
    },
    {
      id: 'analysis',
      title: '분석',
      icon: <FiBarChart2 />,
      items: [
        { label: '리스크 대시보드', path: '/risk-dashboard', icon: <FiAlertTriangle /> },
        { label: '모델 비교', path: '/analysis/model-comparison', icon: <FiLayers /> }
      ]
    },
    {
      id: 'organization',
      title: '조직',
      icon: <FiUsers />,
      items: [
        { label: '조직 관리', path: '/organizations', icon: <FiBriefcase /> },
        { label: '프로젝트', path: '/projects', icon: <FiGrid /> }
      ]
    },
    {
      id: 'settings',
      title: '설정',
      icon: <FiSettings />,
      path: '/settings'
    }
  ];

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const currentSections = prev ?? [];
      if (currentSections.includes(sectionId)) {
        return currentSections.filter(id => id !== sectionId);
      } else {
        return [...currentSections, sectionId];
      }
    });
  };

  const handleSectionClick = (section: MenuSection) => {
    if (section.path) {
      navigate(section.path);
    } else {
      toggleSection(section.id);
    }
  };

  const handleItemClick = (path: string) => {
    navigate(path);
  };

  const isActiveItem = (path: string) => {
    if (path === '/documents' && location.pathname === '/documents') {
      return true;
    }
    if (path === '/agent-hub') {
      return location.pathname.startsWith('/agent-hub');
    }
    if (path !== '/documents' && location.pathname.startsWith(path)) {
      return true;
    }
    return location.pathname === path;
  };

  const isSectionActive = (section: MenuSection) => {
    if (section.path) {
      return location.pathname === section.path || location.pathname.startsWith(section.path + '/') || location.pathname.startsWith(section.path);
    }
    return section.items?.some(item => {
      if (item.path === '/documents') {
        return location.pathname === '/documents' || location.pathname.startsWith('/documents/');
      }
      return location.pathname.startsWith(item.path);
    });
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const formatRelativeDate = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '방금';
    if (minutes < 60) return `${minutes}분 전`;
    if (hours < 24) return `${hours}시간 전`;
    if (days < 7) return `${days}일 전`;
    return date.toLocaleDateString('ko-KR');
  };

  return (
    <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Header */}
      <div className="sidebar-header">
        {!collapsed && (
          <div className="sidebar-logo" onClick={() => navigate('/agent-hub')}>
            <span className="sidebar-logo-icon">⚖️</span>
            <span className="sidebar-logo-text">LawLawKR</span>
          </div>
        )}
        <button className="sidebar-toggle" onClick={onToggle}>
          {collapsed ? <FiMenu /> : <FiChevronLeft />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {(menuSections || []).map(section => (
          <div key={section.id} className="sidebar-section">
            <button
              className={`sidebar-section-header ${isSectionActive(section) ? 'active' : ''}`}
              onClick={() => handleSectionClick(section)}
              title={collapsed ? section.title : undefined}
            >
              <div className="sidebar-section-title">
                <span className="sidebar-section-icon">{section.icon}</span>
                {!collapsed && <span>{section.title}</span>}
              </div>
              {!collapsed && section.items && (
                <span className="sidebar-section-chevron">
                  {(expandedSections ?? []).includes(section.id) ? <FiChevronDown /> : <FiChevronRight />}
                </span>
              )}
            </button>

            {/* Sub Items */}
            {!collapsed && section.items && (expandedSections ?? []).includes(section.id) && (
              <div className="sidebar-section-items">
                {(section.items || []).map(item => (
                  <button
                    key={item.path}
                    className={`sidebar-item ${isActiveItem(item.path) ? 'active' : ''}`}
                    onClick={() => handleItemClick(item.path)}
                  >
                    {item.icon && <span className="sidebar-item-icon">{item.icon}</span>}
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            )}

            {/* AI Assistant - Recent Chats */}
            {!collapsed && section.id === 'ai-assistant' && (expandedSections ?? []).includes(section.id) && (
              <div className="sidebar-chat-section">
                {/* New Chat Button */}
                <button className="sidebar-new-chat-btn" onClick={onNewChat}>
                  <FiPlus />
                  <span>새 대화</span>
                </button>

                {/* Recent Sessions */}
                {Array.isArray(sessions) && sessions.length > 0 && (
                  <div className="sidebar-sessions">
                    <div className="sidebar-sessions-header">최근 대화</div>
                    {(sessions || []).slice(0, 5).map(session => (
                      <div
                        key={session.id}
                        className={`sidebar-session-item ${session.id === currentSessionId ? 'active' : ''}`}
                      >
                        <button
                          className="sidebar-session-btn"
                          onClick={() => onSelectSession?.(session.id)}
                        >
                          <FiMessageSquare className="sidebar-session-icon" />
                          <div className="sidebar-session-content">
                            <span className="sidebar-session-title">
                              {session.title.length > 20
                                ? session.title.substring(0, 20) + '...'
                                : session.title}
                            </span>
                            <span className="sidebar-session-time">
                              {formatRelativeDate(session.timestamp)}
                            </span>
                          </div>
                        </button>
                        <button
                          className="sidebar-session-menu-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            setShowSessionMenu(showSessionMenu === session.id ? null : session.id);
                          }}
                        >
                          <FiMoreHorizontal />
                        </button>
                        {showSessionMenu === session.id && (
                          <div className="sidebar-session-dropdown">
                            <button onClick={() => {
                              onDeleteSession?.(session.id);
                              setShowSessionMenu(null);
                            }}>
                              <FiTrash2 />
                              삭제
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        {isAuthenticated && user ? (
          <div className="sidebar-user">
            {!collapsed ? (
              <>
                <div className="sidebar-user-info">
                  <span className="sidebar-user-name">{user.full_name}</span>
                  <span className="sidebar-user-email">{user.email}</span>
                </div>
                <button className="sidebar-logout-btn" onClick={handleLogout}>
                  <FiLogOut />
                  <span>로그아웃</span>
                </button>
              </>
            ) : (
              <button
                className="sidebar-logout-btn sidebar-logout-collapsed"
                onClick={handleLogout}
                title="로그아웃"
              >
                <FiLogOut />
              </button>
            )}
          </div>
        ) : (
          <div className="sidebar-auth">
            {!collapsed ? (
              <>
                <button className="sidebar-auth-btn" onClick={() => navigate('/login')}>
                  로그인
                </button>
                <button className="sidebar-auth-btn sidebar-auth-signup" onClick={() => navigate('/signup')}>
                  회원가입
                </button>
              </>
            ) : (
              <button
                className="sidebar-auth-btn"
                onClick={() => navigate('/login')}
                title="로그인"
              >
                <FiUsers />
              </button>
            )}
          </div>
        )}
        {!collapsed && (
          <div className="sidebar-version">
            v0.2.0 Beta
          </div>
        )}
      </div>
    </aside>
  );
};

export default AgentHubSidebar;
