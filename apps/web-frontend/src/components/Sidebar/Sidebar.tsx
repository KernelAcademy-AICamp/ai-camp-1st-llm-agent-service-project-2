import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  FiHome,
  FiFileText,
  FiSearch,
  FiBarChart2,
  FiUsers,
  FiSettings,
  FiChevronDown,
  FiChevronRight,
  FiFile,
  FiAlertTriangle,
  FiLayers,
  FiBriefcase,
  FiGrid
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

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [expandedSections, setExpandedSections] = useState<string[]>(['documents', 'analysis']);

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
    if (currentPath.startsWith('/organizations') || currentPath.startsWith('/projects')) {
      if (!expandedSections.includes('organization')) {
        setExpandedSections(prev => [...prev, 'organization']);
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
      return location.pathname === section.path || location.pathname.startsWith(section.path + '/');
    }
    return section.items?.some(item => {
      if (item.path === '/documents') {
        return location.pathname === '/documents' || location.pathname.startsWith('/documents/');
      }
      return location.pathname.startsWith(item.path);
    });
  };

  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        {menuSections.map(section => (
          <div key={section.id} className="sidebar-section">
            <button
              className={`sidebar-section-header ${isSectionActive(section) ? 'active' : ''}`}
              onClick={() => handleSectionClick(section)}
            >
              <div className="sidebar-section-title">
                <span className="sidebar-section-icon">{section.icon}</span>
                <span>{section.title}</span>
              </div>
              {section.items && (
                <span className="sidebar-section-chevron">
                  {expandedSections.includes(section.id) ? <FiChevronDown /> : <FiChevronRight />}
                </span>
              )}
            </button>
            {section.items && expandedSections.includes(section.id) && (
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
      <div className="sidebar-footer">
        <div className="sidebar-version">
          v0.2.0 Beta
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
