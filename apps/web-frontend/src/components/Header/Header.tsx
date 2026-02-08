import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Header.css';

const Header: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout, isAuthenticated } = useAuth();
  const [isVisible, setIsVisible] = useState(true);
  const lastScrollY = useRef(0);

  const scrollUpDistance = useRef(0);

  useEffect(() => {
    const handleScroll = (e: Event) => {
      const target = e.target as HTMLElement;
      const currentScrollY = target.scrollTop;
      const scrollDelta = lastScrollY.current - currentScrollY;

      // 스크롤 내리면 헤더 숨김 (10px 이상 스크롤 시)
      if (currentScrollY > lastScrollY.current && currentScrollY > 10) {
        setIsVisible(false);
        document.querySelector('.layout')?.classList.add('header-hidden-mode');
        scrollUpDistance.current = 0; // 위로 스크롤 거리 리셋
      }
      // 스크롤 올릴 때 - 100px 이상 올려야 헤더 표시
      else if (scrollDelta > 0) {
        scrollUpDistance.current += scrollDelta;
        if (scrollUpDistance.current > 100 || currentScrollY < 10) {
          setIsVisible(true);
          document.querySelector('.layout')?.classList.remove('header-hidden-mode');
        }
      }

      lastScrollY.current = currentScrollY;
    };

    // layout-main 요소에서 스크롤 감지
    const mainElement = document.querySelector('.layout-main');
    if (mainElement) {
      mainElement.addEventListener('scroll', handleScroll, { passive: true });
      return () => mainElement.removeEventListener('scroll', handleScroll);
    }

    // fallback: window 스크롤
    window.addEventListener('scroll', handleScroll as any, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll as any);
  }, []);

  const handleLogoClick = () => {
    navigate('/');
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className={`header ${isVisible ? 'header-visible' : 'header-hidden'}`}>
      <div className="header-left">
        <div className="header-logo" onClick={handleLogoClick}>
          <span className="header-logo-icon">⚖️</span>
          <h1 className="header-title">LawLawKR</h1>
        </div>
        <div className="header-subtitle">
          완전 로컬 형사법 AI 어시스턴트
        </div>
      </div>

      {isAuthenticated ? (
        <div className="header-user">
          <div className="header-user-info">
            <span className="header-user-name">{user?.full_name}</span>
            <span className="header-user-email">{user?.email}</span>
          </div>
          <button className="header-logout-button" onClick={handleLogout}>
            로그아웃
          </button>
        </div>
      ) : (
        <div className="header-auth-buttons">
          <button className="header-btn-login" onClick={() => navigate('/login')}>
            로그인
          </button>
          <button className="header-btn-signup" onClick={() => navigate('/signup')}>
            회원가입
          </button>
        </div>
      )}
    </header>
  );
};

export default Header;