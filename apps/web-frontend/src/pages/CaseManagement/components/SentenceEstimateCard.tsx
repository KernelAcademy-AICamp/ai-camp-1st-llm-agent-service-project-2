import React from 'react';
import { FiActivity, FiInfo } from 'react-icons/fi';
import { ExpectedSentence } from '../../../types';
import './CriminalCards.css';

interface SentenceEstimateCardProps {
  sentence: ExpectedSentence;
}

const SentenceEstimateCard: React.FC<SentenceEstimateCardProps> = ({ sentence }) => {
  const probabilityPercent = Math.round(sentence.suspended_probability * 100);

  // 집행유예 가능성에 따른 색상 결정
  const getProbabilityColor = (prob: number) => {
    if (prob >= 70) return '#10b981'; // 녹색 (높음)
    if (prob >= 40) return '#f59e0b'; // 주황색 (보통)
    return '#ef4444'; // 빨간색 (낮음)
  };

  const probabilityColor = getProbabilityColor(probabilityPercent);

  return (
    <div className="criminal-card sentence-estimate-card">
      <div className="card-header">
        <div className="card-title">
          <FiActivity className="card-icon" />
          <h4>양형 예측</h4>
        </div>
      </div>

      <div className="card-content">
        <div className="sentence-main">
          {/* 예상 형량 범위 */}
          <div className="sentence-range">
            <span className="range-label">예상 형량</span>
            <span className="range-value">{sentence.range}</span>
          </div>

          {/* 집행유예 가능성 */}
          <div className="suspended-probability">
            <span className="prob-label">집행유예 가능성</span>
            <div className="prob-display">
              <div className="prob-circle" style={{ borderColor: probabilityColor }}>
                <span className="prob-value" style={{ color: probabilityColor }}>
                  {probabilityPercent}%
                </span>
              </div>
              <div className="prob-bar-container">
                <div
                  className="prob-bar"
                  style={{
                    width: `${probabilityPercent}%`,
                    backgroundColor: probabilityColor
                  }}
                />
              </div>
              <span className="prob-status" style={{ color: probabilityColor }}>
                {probabilityPercent >= 70 ? '높음' : probabilityPercent >= 40 ? '보통' : '낮음'}
              </span>
            </div>
          </div>
        </div>

        {/* 산정 근거 */}
        {sentence.reasoning && (
          <div className="sentence-reasoning">
            <div className="reasoning-header">
              <FiInfo />
              <span>산정 근거</span>
            </div>
            <p>{sentence.reasoning}</p>
          </div>
        )}

        {/* 면책 고지 */}
        <div className="disclaimer">
          이 예측은 유사 판례 분석을 기반으로 한 참고 정보입니다.
          실제 양형은 재판부의 판단에 따라 달라질 수 있습니다.
        </div>
      </div>
    </div>
  );
};

export default SentenceEstimateCard;
