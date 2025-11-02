import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { FiSearch, FiFolder, FiFileText, FiSettings, FiChevronDown, FiChevronRight } from 'react-icons/fi';
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
  items: MenuItem[];
}

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [expandedSections, setExpandedSections] = useState<string[]>(['research']);

  const menuSections: MenuSection[] = [
    {
      id: 'research',
      title: '법률 리서치',
      icon: <FiSearch />,
      items: [
        { label: 'AI 질의응답', path: '/research/ai' },
        { label: '판례 검색', path: '/research/cases' },
        { label: '법령 검색', path: '/research/laws' },
        { label: '통합 검색', path: '/research/all' },
        { label: '검색 기록', path: '/research/history' }
      ]
    },
    {
      id: 'cases',
      title: '사건 관리',
      icon: <FiFolder />,
      items: [
        { label: '새 사건', path: '/cases/new' },
        { label: '진행 중', path: '/cases/active' },
        { label: '종료 사건', path: '/cases/closed' },
        { label: '문서 업로드', path: '/cases/upload' },
        { label: 'AI 분석', path: '/cases/analysis' }
      ]
    },
    {
      id: 'docs',
      title: '문서 작성',
      icon: <FiFileText />,
      items: [
        { label: '새 문서', path: '/docs/new' },
        { label: '템플릿', path: '/docs/templates' },
        { label: '작성 중', path: '/docs/drafts' },
        { label: '완료 문서', path: '/docs/completed' },
        { label: 'AI 어시스트', path: '/docs/assist' }
      ]
    },
    {
      id: 'settings',
      title: '설정',
      icon: <FiSettings />,
      items: [
        { label: 'AI 모델', path: '/settings/model' },
        { label: '데이터베이스', path: '/settings/database' },
        { label: '환경설정', path: '/settings/preferences' }
      ]
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

  const handleItemClick = (path: string) => {
    navigate(path);
  };

  const isActiveItem = (path: string) => {
    return location.pathname === path;
  };

  const isSectionActive = (section: MenuSection) => {
    return section.items.some(item => location.pathname.startsWith(item.path));
  };

  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        {menuSections.map(section => (
          <div key={section.id} className="sidebar-section">
            <button
              className={`sidebar-section-header ${isSectionActive(section) ? 'active' : ''}`}
              onClick={() => toggleSection(section.id)}
            >
              <div className="sidebar-section-title">
                <span className="sidebar-section-icon">{section.icon}</span>
                <span>{section.title}</span>
              </div>
              <span className="sidebar-section-chevron">
                {expandedSections.includes(section.id) ? <FiChevronDown /> : <FiChevronRight />}
              </span>
            </button>
            {expandedSections.includes(section.id) && (
              <div className="sidebar-section-items">
                {section.items.map(item => (
                  <button
                    key={item.path}
                    className={`sidebar-item ${isActiveItem(item.path) ? 'active' : ''}`}
                    onClick={() => handleItemClick(item.path)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-version">
          v0.1.0 Beta
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;