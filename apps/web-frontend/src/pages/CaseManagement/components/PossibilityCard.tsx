import React from 'react';
import { FiCheckCircle, FiAlertTriangle, FiXCircle } from 'react-icons/fi';
import { CriminalCaseAnalysis } from '../../../types';
import './SimpleCards.css';

interface PossibilityCardProps {
  analysis: CriminalCaseAnalysis;
}

type PossibilityLevel = 'high' | 'medium' | 'low';

const PossibilityCard: React.FC<PossibilityCardProps> = ({ analysis }) => {
  // 구성요건 충족률로 고소 가능성 계산
  const calculatePossibility = (): { level: PossibilityLevel; percentage: number } => {
    const elements = analysis.crime_elements;
    if (!elements || (!elements.objective?.length && !elements.subjective?.length)) {
      return { level: 'medium', percentage: 50 };
    }

    const allElements = [
      ...(elements.objective || []),
      ...(elements.subjective || []),
    ];

    if (allElements.length === 0) {
      return { level: 'medium', percentage: 50 };
    }

    const fulfilledCount = allElements.filter(e => e.fulfilled).length;
    const percentage = Math.round((fulfilledCount / allElements.length) * 100);

    let level: PossibilityLevel;
    if (percentage >= 70) {
      level = 'high';
    } else if (percentage >= 40) {
      level = 'medium';
    } else {
      level = 'low';
    }

    return { level, percentage };
  };

  const { level, percentage } = calculatePossibility();

  const levelConfig = {
    high: {
      icon: FiCheckCircle,
      text: '높음',
      description: '고소/고발이 받아들여질 가능성이 높습니다.',
      advice: '증거를 잘 정리해서 경찰서에 방문하세요.',
      color: '#10b981',
      bgColor: '#ecfdf5',
    },
    medium: {
      icon: FiAlertTriangle,
      text: '보통',
      description: '가능성은 있지만, 추가 증거가 있으면 더 좋습니다.',
      advice: '부족한 증거를 보강하면 성공 가능성이 높아집니다.',
      color: '#f59e0b',
      bgColor: '#fffbeb',
    },
    low: {
      icon: FiXCircle,
      text: '낮음',
      description: '현재 증거만으로는 인정받기 어려울 수 있습니다.',
      advice: '추가 증거 수집이나 전문가 상담을 권장합니다.',
      color: '#ef4444',
      bgColor: '#fef2f2',
    },
  };

  const config = levelConfig[level];
  const IconComponent = config.icon;

  return (
    <div
      className="simple-card possibility-card"
      style={{ backgroundColor: config.bgColor, borderColor: config.color }}
    >
      <div className="card-header">
        <h4>
          <span className="card-icon" style={{ color: config.color }}>
            <IconComponent />
          </span>
          고소 가능성
        </h4>
      </div>

      <div className="possibility-content">
        <div className="possibility-indicator" style={{ color: config.color }}>
          <span className="level-text">{config.text}</span>
          <span className="percentage">({percentage}%)</span>
        </div>

        <div className="possibility-bar">
          <div
            className="possibility-fill"
            style={{
              width: `${percentage}%`,
              backgroundColor: config.color,
            }}
          />
        </div>

        <p className="description">{config.description}</p>
        <p className="advice">
          <strong>Tip:</strong> {config.advice}
        </p>
      </div>
    </div>
  );
};

export default PossibilityCard;
