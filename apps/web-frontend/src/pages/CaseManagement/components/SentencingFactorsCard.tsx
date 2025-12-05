import React from 'react';
import { FiThumbsUp, FiThumbsDown, FiBarChart2 } from 'react-icons/fi';
import { SentencingFactors } from '../../../types';
import './CriminalCards.css';

interface SentencingFactorsCardProps {
  factors: SentencingFactors;
}

const SentencingFactorsCard: React.FC<SentencingFactorsCardProps> = ({ factors }) => {
  return (
    <div className="criminal-card sentencing-factors-card">
      <div className="card-header">
        <div className="card-title">
          <FiBarChart2 className="card-icon" />
          <h4>양형인자</h4>
        </div>
      </div>

      <div className="card-content">
        <div className="factors-grid">
          {/* 유리한 정상 */}
          <div className="factor-section favorable">
            <div className="factor-header">
              <FiThumbsUp className="factor-icon favorable" />
              <span>유리한 정상 ({factors.favorable.length})</span>
            </div>
            <div className="factor-list">
              {factors.favorable.length > 0 ? (
                factors.favorable.map((factor, idx) => (
                  <span key={idx} className="factor-tag favorable">
                    {factor}
                  </span>
                ))
              ) : (
                <span className="no-factors">없음</span>
              )}
            </div>
          </div>

          {/* 불리한 정상 */}
          <div className="factor-section unfavorable">
            <div className="factor-header">
              <FiThumbsDown className="factor-icon unfavorable" />
              <span>불리한 정상 ({factors.unfavorable.length})</span>
            </div>
            <div className="factor-list">
              {factors.unfavorable.length > 0 ? (
                factors.unfavorable.map((factor, idx) => (
                  <span key={idx} className="factor-tag unfavorable">
                    {factor}
                  </span>
                ))
              ) : (
                <span className="no-factors">없음</span>
              )}
            </div>
          </div>
        </div>

        {/* 양형인자 밸런스 */}
        <div className="factor-balance">
          <div className="balance-bar">
            <div
              className="balance-favorable"
              style={{
                width: `${Math.max(10, (factors.favorable.length / (factors.favorable.length + factors.unfavorable.length + 0.01)) * 100)}%`
              }}
            />
            <div
              className="balance-unfavorable"
              style={{
                width: `${Math.max(10, (factors.unfavorable.length / (factors.favorable.length + factors.unfavorable.length + 0.01)) * 100)}%`
              }}
            />
          </div>
          <div className="balance-labels">
            <span>유리</span>
            <span>불리</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SentencingFactorsCard;
