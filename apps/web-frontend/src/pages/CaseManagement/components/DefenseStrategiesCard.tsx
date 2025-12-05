import React from 'react';
import { FiShield, FiChevronRight } from 'react-icons/fi';
import './CriminalCards.css';

interface DefenseStrategiesCardProps {
  strategies: string[];
}

const DefenseStrategiesCard: React.FC<DefenseStrategiesCardProps> = ({ strategies }) => {
  if (!strategies || strategies.length === 0) {
    return null;
  }

  return (
    <div className="criminal-card defense-strategies-card">
      <div className="card-header">
        <div className="card-title">
          <FiShield className="card-icon" />
          <h4>변호 전략 제안</h4>
        </div>
        <span className="strategy-count">{strategies.length}개 전략</span>
      </div>

      <div className="card-content">
        <div className="strategies-list">
          {strategies.map((strategy, idx) => (
            <div key={idx} className="strategy-item">
              <div className="strategy-number">
                <span>{idx + 1}</span>
              </div>
              <div className="strategy-content">
                <span>{strategy}</span>
              </div>
              <FiChevronRight className="strategy-arrow" />
            </div>
          ))}
        </div>

        <div className="strategies-note">
          제안된 전략은 AI 분석 결과입니다.
          담당 변호사와 상의하여 구체적인 변호 전략을 수립하세요.
        </div>
      </div>
    </div>
  );
};

export default DefenseStrategiesCard;
