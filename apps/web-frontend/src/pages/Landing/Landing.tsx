/**
 * LawLawKR Landing Page
 * 홍보용 랜딩 페이지 - website/index.html을 React로 변환
 */

import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Landing.css';

const Landing: React.FC = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Smooth scroll for anchor links
    const handleAnchorClick = (e: Event) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'A' && target.getAttribute('href')?.startsWith('#')) {
        e.preventDefault();
        const href = target.getAttribute('href');
        if (href) {
          const element = document.querySelector(href);
          if (element) {
            element.scrollIntoView({
              behavior: 'smooth',
              block: 'start'
            });
          }
        }
      }
    };

    document.addEventListener('click', handleAnchorClick);

    // Header scroll effect
    const handleScroll = () => {
      const header = document.querySelector('.landing-header');
      if (header) {
        if (window.scrollY > 50) {
          header.classList.add('scrolled');
        } else {
          header.classList.remove('scrolled');
        }
      }
    };

    window.addEventListener('scroll', handleScroll);

    // Intersection Observer for fade-in animations
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, observerOptions);

    // Observe all feature rows, pricing cards, and qdora features
    document.querySelectorAll('.landing-feature-row, .landing-pricing-card, .landing-qdora-feature').forEach(el => {
      observer.observe(el);
    });

    return () => {
      document.removeEventListener('click', handleAnchorClick);
      window.removeEventListener('scroll', handleScroll);
      observer.disconnect();
    };
  }, []);

  const handleDownloadClick = (platform: string) => {
    alert(`${platform} 버전 준비 중입니다`);
  };

  return (
    <div className="landing-page">
      {/* Header */}
      <header className="landing-header">
        <div className="landing-container">
          <div className="landing-header-content">
            <a href="/" className="landing-logo">
              <span className="landing-logo-text">LawLawKR</span>
            </a>

            <nav className="landing-nav">
              <a href="#intro" className="landing-nav-link">LawLawKR 소개</a>
              <a href="#features" className="landing-nav-link">주요 기능</a>
              <a href="#qdora" className="landing-nav-link">QDoRA 어댑터</a>
              <a href="#pricing" className="landing-nav-link">요금 안내</a>
              <a href="#download" className="landing-nav-link">다운로드</a>
            </nav>

            <div className="landing-header-actions">
              <button className="landing-btn-login" onClick={() => navigate('/login')}>로그인</button>
              <button className="landing-btn-trial" onClick={() => navigate('/app')}>무료체험 시작</button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="landing-hero" id="intro">
        <div className="landing-container">
          <div className="landing-hero-content">
            <h1 className="landing-hero-title">
              형사법 전문 AI 어시스턴트<br />
              <span className="landing-highlight">LawLawKR</span>
            </h1>
            <p className="landing-hero-subtitle">
              QDoRA 어댑터 기반의 형사법 특화 AI로<br />
              완전히 로컬에서 안전하게 법률 업무를 수행하세요
            </p>
            <button className="landing-btn-cta" onClick={() => navigate('/app')}>무료체험 시작</button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="landing-features">
        <div className="landing-container">
          <h2 className="landing-section-title">주요 기능</h2>

          {/* Feature 1: 로컬 법률 AI */}
          <div className="landing-feature-row">
            <div className="landing-feature-content">
              <div className="landing-feature-icon-large">💬</div>
              <h3 className="landing-feature-title-large">로컬 법률 AI</h3>
              <p className="landing-feature-description">
                복잡한 법률 질문에도, LawLawKR은 정확하고 신뢰할 수 있는 답변을 제공합니다.
                국내 법률 환경에 최적화된 자체 AI 모델이 방대한 법률 데이터를 기반으로
                리서치에 드는 시간을 획기적으로 줄이고 실무 효율을 높입니다.
              </p>
              <ul className="landing-feature-list-new">
                <li>AI 기반 법률 검색</li>
                <li>판례/법령 실시간 분석</li>
                <li>형사법 전문 자문</li>
              </ul>
            </div>
            <div className="landing-feature-visual">
              <div className="landing-feature-mockup">
                <div className="landing-mockup-content">🔍 AI 검색 화면</div>
              </div>
            </div>
          </div>

          {/* Feature 2: 법률 문서 정리 */}
          <div className="landing-feature-row reverse">
            <div className="landing-feature-visual">
              <div className="landing-feature-mockup">
                <div className="landing-mockup-content">📄 문서 분석 화면</div>
              </div>
            </div>
            <div className="landing-feature-content">
              <div className="landing-feature-icon-large">📄</div>
              <h3 className="landing-feature-title-large">법률 문서 정리</h3>
              <p className="landing-feature-description">
                판결문, 사건 자료, 증거 등 복잡한 법률 문서를 AI가 자동으로 분석하고 요약합니다.
                핵심 내용을 빠르게 파악하고, 관련 판례와 법령을 연결하여
                효율적인 사건 준비가 가능합니다.
              </p>
              <ul className="landing-feature-list-new">
                <li>판결문 자동 요약</li>
                <li>사건 자료 체계적 분류</li>
                <li>증거 문서 관련성 평가</li>
              </ul>
            </div>
          </div>

          {/* Feature 3: 법률 문서 작성 */}
          <div className="landing-feature-row">
            <div className="landing-feature-content">
              <div className="landing-feature-icon-large">✍️</div>
              <h3 className="landing-feature-title-large">법률 문서 작성</h3>
              <p className="landing-feature-description">
                법률 의견서, 판결문 초안, 계약서 등 다양한 법률 문서를 AI가 자동으로 생성합니다.
                템플릿 기반의 문서 작성부터 맞춤형 내용 생성까지,
                실무에 바로 활용 가능한 문서를 신속하게 작성할 수 있습니다.
              </p>
              <ul className="landing-feature-list-new">
                <li>판결문 초안 자동 생성</li>
                <li>법률 의견서 작성 어시스트</li>
                <li>계약서 검토 및 수정 제안</li>
              </ul>
            </div>
            <div className="landing-feature-visual">
              <div className="landing-feature-mockup">
                <div className="landing-mockup-content">✍️ 문서 작성 화면</div>
              </div>
            </div>
          </div>

          {/* Feature 4: 사건 관리 */}
          <div className="landing-feature-row reverse">
            <div className="landing-feature-visual">
              <div className="landing-feature-mockup">
                <div className="landing-mockup-content">📁 사건 관리 화면</div>
              </div>
            </div>
            <div className="landing-feature-content">
              <div className="landing-feature-icon-large">📁</div>
              <h3 className="landing-feature-title-large">사건 관리</h3>
              <p className="landing-feature-description">
                사건의 전체 타임라인을 한눈에 파악하고, 증거와 문서를 체계적으로 관리합니다.
                중요한 기한과 일정을 놓치지 않도록 알림 기능을 제공하며,
                AI가 사건의 진행 상황을 분석하여 최적의 전략을 제안합니다.
              </p>
              <ul className="landing-feature-list-new">
                <li>사건 타임라인 자동 생성</li>
                <li>증거 및 문서 체계적 분류</li>
                <li>기한 및 일정 자동 알림</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* QDoRA Section */}
      <section id="qdora" className="landing-qdora">
        <div className="landing-container">
          <h2 className="landing-section-title">QDoRA 어댑터</h2>
          <p className="landing-section-subtitle">형사법에 특화된 Domain-Specific Adapter</p>
          <div className="landing-qdora-grid">
            <div className="landing-qdora-feature">
              <div className="landing-qdora-icon">🎓</div>
              <h3>전문성</h3>
              <p>형사법 판례와 법령으로 특화 학습된 경량 어댑터</p>
            </div>
            <div className="landing-qdora-feature">
              <div className="landing-qdora-icon">⚡</div>
              <h3>효율성</h3>
              <p>150MB 경량 모델로 빠른 응답 속도 제공</p>
            </div>
            <div className="landing-qdora-feature">
              <div className="landing-qdora-icon">🔒</div>
              <h3>프라이버시</h3>
              <p>완전히 로컬에서 실행되는 안전한 AI</p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="landing-pricing">
        <div className="landing-container">
          <h2 className="landing-section-title">요금 안내</h2>
          <div className="landing-pricing-grid">
            <div className="landing-pricing-card">
              <h3 className="landing-pricing-title">무료 버전</h3>
              <div className="landing-pricing-price">₩0</div>
              <p className="landing-pricing-desc">웹 기반</p>
              <ul className="landing-pricing-features">
                <li className="check">✅ 기본 법률 검색</li>
                <li className="check">✅ 간단한 문서 분석</li>
                <li className="check">✅ AI 대화 (기본)</li>
                <li className="cross">❌ QDoRA 어댑터</li>
                <li className="cross">❌ 사건 관리</li>
                <li className="cross">❌ 오프라인 사용</li>
              </ul>
              <button className="landing-btn-pricing" onClick={() => navigate('/app')}>지금 시작하기</button>
            </div>

            <div className="landing-pricing-card featured">
              <div className="landing-pricing-badge">추천</div>
              <h3 className="landing-pricing-title">데스크톱 앱</h3>
              <div className="landing-pricing-price">무료</div>
              <p className="landing-pricing-desc">다운로드 필요</p>
              <ul className="landing-pricing-features">
                <li className="check">✅ 모든 무료 버전 기능</li>
                <li className="check">✅ QDoRA 어댑터</li>
                <li className="check">✅ 사건 관리</li>
                <li className="check">✅ 문서 편집기</li>
                <li className="check">✅ 오프라인 사용</li>
                <li className="check">✅ 로컬 데이터 저장</li>
              </ul>
              <a href="#download" className="landing-btn-pricing">다운로드</a>
            </div>
          </div>
        </div>
      </section>

      {/* Download Section */}
      <section id="download" className="landing-download">
        <div className="landing-container">
          <h2 className="landing-section-title">데스크톱 앱 다운로드</h2>
          <p className="landing-section-subtitle">macOS, Windows, Linux 지원</p>
          <div className="landing-download-grid">
            <button className="landing-download-btn" onClick={() => handleDownloadClick('macOS')}>
              <span className="landing-download-icon">🍎</span>
              <span>macOS</span>
            </button>
            <button className="landing-download-btn" onClick={() => handleDownloadClick('Windows')}>
              <span className="landing-download-icon">🪟</span>
              <span>Windows</span>
            </button>
            <button className="landing-download-btn" onClick={() => handleDownloadClick('Linux')}>
              <span className="landing-download-icon">🐧</span>
              <span>Linux</span>
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-container">
          <p className="landing-footer-text">© 2025 LawLawKR. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
