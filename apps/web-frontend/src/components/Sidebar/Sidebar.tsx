import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
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
  FiLogOut,
  FiMenu,
  FiMessageSquare
} from 'react-icons/fi';
import './Sidebar.css';

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
  path?: string;  // Direct link (no submenu)
}

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAuthenticated } = useAuth();
  const [expandedSections, setExpandedSections] = useState<string[]>(['documents', 'analysis', 'ai-assistant']);

  // Auto-expand section when navigating to a page within it
  useEffect(() => {
    const currentPath = location.pathname;

    if (currentPath.startsWith('/documents') || currentPath.startsWith('/research')) {
      if (!expandedSections.includes('documents')) {
        setExpandedSections(prev => [...prev, 'documents']);
      }
    }
    if (currentPath.startsWith('/risk-dashboard') || currentPath.startsWith('/analysis')) {
      if (!expandedSections.includes('analysis')) {
        setExpandedSections(prev => [...prev, 'analysis']);
      }
    }
    if (currentPath.startsWith('/agent-hub')) {
      if (!expandedSections.includes('ai-assistant')) {
        setExpandedSections(prev => [...prev, 'ai-assistant']);
      }
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
      items: [
        { label: 'Agent Hub', path: '/agent-hub', icon: <FiMessageSquare /> },
        { label: '법률 리서치', path: '/research', icon: <FiSearch /> }
      ]
    },
    {
      id: 'documents',
      title: '문서',
      icon: <FiFileText />,
      items: [
        { label: '문서 관리', path: '/documents', icon: <FiFile /> },
        { label: '판례 검색', path: '/documents/research', icon: <FiBriefcase /> }
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
      id: 'settings',
      title: '설정',
      icon: <FiSettings />,
      path: '/settings'
    }
  ];

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      if (prev.includes(sectionId)) {
        return prev.filter(id => id !== sectionId);
      } else {
        return [...prev, sectionId];
      }
    });
  };

  const handleSectionClick = (section: MenuSection) => {
    if (section.path) {
      // Direct navigation for sections without subitems
      navigate(section.path);
    } else {
      // Toggle expansion for sections with subitems
      toggleSection(section.id);
    }
  };

  const handleItemClick = (path: string) => {
    navigate(path);
  };

  const isActiveItem = (path: string) => {
    // Exact match for specific paths
    if (path === '/documents' && location.pathname === '/documents') {
      return true;
    }
    // Prefix match for other paths
    if (path !== '/documents' && location.pathname.startsWith(path)) {
      return true;
    }
    return location.pathname === path;
  };

  const isSectionActive = (section: MenuSection) => {
    if (section.path) {
      // Special case for /agent-hub to match all subpaths
      if (section.path === '/agent-hub') {
        return location.pathname.startsWith('/agent-hub');
      }
      return location.pathname === section.path || location.pathname.startsWith(section.path + '/');
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

  return (
    <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Header with Logo and Toggle */}
      <div className="sidebar-header">
        {!collapsed && (
          <div className="sidebar-logo" onClick={() => navigate('/')}>
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
        {menuSections.map(section => (
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
                  {expandedSections.includes(section.id) ? <FiChevronDown /> : <FiChevronRight />}
                </span>
              )}
            </button>
            {!collapsed && section.items && expandedSections.includes(section.id) && (
              <div className="sidebar-section-items">
                {section.items.map(item => (
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
          </div>
        ))}
      </nav>

      {/* Footer with User Info */}
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

export default Sidebar;
