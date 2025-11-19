/**
 * LawLawKR Home Page
 * SuperLawyer 스타일 - 왼쪽 기능 목록, 오른쪽 상세 설명
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiMessageSquare, FiFileText, FiEdit, FiFolder, FiChevronRight } from 'react-icons/fi';
import './Home.css';

interface Feature {
  id: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  details: string[];
  path: string;
  gradient: string;
}

const Home: React.FC = () => {
  const navigate = useNavigate();
  const [selectedFeature, setSelectedFeature] = useState<string>('ai-chat');

  const features: Feature[] = [
    {
      id: 'ai-chat',
      icon: <FiMessageSquare />,
      title: '로컬 법률 AI',
      description: '복잡한 법률 질문에도, LawLawKR은 정확하고 신뢰할 수 있는 답변을 제공합니다. 국내 법률 환경에 최적화된 자체 AI 모델이 아키텍처, 자체 보유한 방대한 법률 데이터를 기반으로 리서치에 드는 시간을 획기적으로 줄이고 실무 효율을 높입니다.',
      details: [
        'AI가 생성한 답변 내에서 인용된 판례나 법령이 해당 답변의 취지와 잘 맞는지를',
        'AI가 스스로 다시 검토합니다. 인용 자료를 모두 읽지 않아도 타당성을 빠르게 확인할 수 있어,',
        '단순 정보 제공을 넘어 근거의 신뢰성까지 검증할 수 있는 리서치 도구입니다.'
      ],
      path: '/research',
      gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    },
    {
      id: 'doc-analyze',
      icon: <FiFileText />,
      title: '법률 문서 정리',
      description: '판결문, 사건 자료, 증거 등 복잡한 법률 문서를 AI가 자동으로 분석하고 요약합니다. 핵심 내용을 빠르게 파악하고, 관련 판례와 법령을 연결하여 효율적인 사건 준비가 가능합니다.',
      details: [
        '판결문 자동 요약 및 핵심 쟁점 추출',
        '사건 자료의 체계적 분류 및 분석',
        '증거 문서의 관련성 평가 및 정리',
        'AI 기반 문서 간 연관성 분석'
      ],
      path: '/cases',
      gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
    },
    {
      id: 'doc-editor',
      icon: <FiEdit />,
      title: '법률 문서 작성',
      description: '법률 의견서, 판결문 초안, 계약서 등 다양한 법률 문서를 AI가 자동으로 생성합니다. 템플릿 기반의 문서 작성부터 맞춤형 내용 생성까지, 실무에 바로 활용 가능한 문서를 신속하게 작성할 수 있습니다.',
      details: [
        '판결문 초안 자동 생성 및 편집',
        '법률 의견서 작성 어시스트',
        '계약서 검토 및 수정 제안',
        '다양한 법률 문서 템플릿 제공'
      ],
      path: '/docs',
      gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
    },
    {
      id: 'case-mgmt',
      icon: <FiFolder />,
      title: '사건 관리',
      description: '사건의 전체 타임라인을 한눈에 파악하고, 증거와 문서를 체계적으로 관리합니다. 중요한 기한과 일정을 놓치지 않도록 알림 기능을 제공하며, AI가 사건의 진행 상황을 분석하여 최적의 전략을 제안합니다.',
      details: [
        '사건 타임라인 자동 생성 및 관리',
        '증거 및 문서 체계적 분류',
        '기한 및 일정 자동 알림',
        'AI 기반 사건 진행 상황 분석'
      ],
      path: '/cases',
      gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
    }
  ];

  const selected = features.find(f => f.id === selectedFeature) || features[0];

  const handleFeatureClick = (featureId: string) => {
    setSelectedFeature(featureId);
  };

  const handleStartClick = () => {
    navigate(selected.path);
  };

  return (
    <div className="home-page-superlawyer">
      <div className="home-container">
        <h1 className="home-main-title">주요 기능 안내</h1>

        <div className="home-content">
          {/* 왼쪽 기능 목록 */}
          <div className="features-list">
            {features.map((feature) => (
              <button
                key={feature.id}
                className={`feature-item ${selectedFeature === feature.id ? 'active' : ''}`}
                onClick={() => handleFeatureClick(feature.id)}
              >
                <div className="feature-item-icon" style={{ background: feature.gradient }}>
                  {feature.icon}
                </div>
                <span className="feature-item-title">{feature.title}</span>
                {selectedFeature === feature.id && (
                  <FiChevronRight className="feature-item-indicator" />
                )}
              </button>
            ))}
          </div>

          {/* 오른쪽 상세 설명 */}
          <div className="feature-detail">
            <div className="feature-detail-content">
              <div className="feature-detail-header">
                <div className="feature-detail-icon" style={{ background: selected.gradient }}>
                  {selected.icon}
                </div>
                <h2 className="feature-detail-title">{selected.title}</h2>
              </div>

              <p className="feature-detail-description">{selected.description}</p>

              <div className="feature-detail-list">
                {selected.details.map((detail, index) => (
                  <div key={index} className="feature-detail-item">
                    {detail}
                  </div>
                ))}
              </div>

              <button className="feature-start-button" onClick={handleStartClick}>
                시작하기 →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
