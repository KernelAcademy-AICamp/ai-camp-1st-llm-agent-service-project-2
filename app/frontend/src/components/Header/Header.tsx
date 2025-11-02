import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Header.css';

const Header: React.FC = () => {
  const navigate = useNavigate();

  const handleLogoClick = () => {
    navigate('/');
  };

  return (
    <header className="header">
      <div className="header-logo" onClick={handleLogoClick}>
        <span className="header-logo-icon">⚖️</span>
        <h1 className="header-title">LawLawKR</h1>
      </div>
      <div className="header-subtitle">
        완전 로컬 형사법 AI 어시스턴트
      </div>
    </header>
  );
};

export default Header;