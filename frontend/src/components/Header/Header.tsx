import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Header.css';

const Header: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout, isAuthenticated } = useAuth();

  const handleLogoClick = () => {
    navigate('/');
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="header">
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