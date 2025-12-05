import React from 'react';
import { FiInfo, FiAlertCircle } from 'react-icons/fi';
import { ExpectedSentence } from '../../../types';
import './SimpleCards.css';

interface ExpectedResultCardProps {
  sentence: ExpectedSentence;
  crimeType: string;
  role?: 'victim' | 'defendant';
}

const ExpectedResultCard: React.FC<ExpectedResultCardProps> = ({
  sentence,
  crimeType,
  role = 'victim',
}) => {
  // 형량 범위를 쉬운 말로 변환
  const simplifyRange = (range: string): string => {
    if (!range) return '판단 어려움';

    // 원본 그대로 표시하되, 추가 설명 제공
    return range;
  };

  // 집행유예 확률을 쉬운 말로
  const describeSuspendedProbability = (prob: number): { text: string; level: string } => {
    if (prob >= 0.7) {
      return {
        text: '실형보다 집행유예(감옥 안 가는 것) 가능성이 높습니다',
        level: 'high',
      };
    } else if (prob >= 0.4) {
      return {
        text: '집행유예와 실형 가능성이 비슷합니다',
        level: 'medium',
      };
    } else {
      return {
        text: '실형(감옥에 가는 것) 가능성이 높습니다',
        level: 'low',
      };
    }
  };

  const suspendedInfo = describeSuspendedProbability(sentence?.suspended_probability || 0.5);

  // 피해자/피의자 관점에 따른 메시지
  const perspectiveMessage =
    role === 'victim'
      ? '가해자가 받을 수 있는 처벌 수준입니다.'
      : '받을 수 있는 처벌 수준입니다.';

  // 처벌 종류 설명
  const punishmentTypes = [
    { type: '징역', desc: '교도소에서 일정 기간 복역' },
    { type: '금고', desc: '교도소 수감 (노동 의무 없음)' },
    { type: '벌금', desc: '일정 금액을 납부' },
    { type: '집행유예', desc: '일정 기간 문제없으면 형 면제' },
  ];

  return (
    <div className="simple-card expected-result-card">
      <div className="card-header">
        <h4>예상 처벌 수위</h4>
        <span className="card-subtitle">{perspectiveMessage}</span>
      </div>

      <div className="result-content">
        {/* 예상 형량 */}
        <div className="result-main">
          <div className="result-label">예상 처벌 범위</div>
          <div className="result-value">{simplifyRange(sentence?.range || '판단 필요')}</div>
        </div>

        {/* 집행유예 가능성 */}
        <div className={`suspended-probability level-${suspendedInfo.level}`}>
          <div className="probability-bar">
            <div
              className="probability-fill"
              style={{ width: `${(sentence?.suspended_probability || 0.5) * 100}%` }}
            />
          </div>
          <div className="probability-text">{suspendedInfo.text}</div>
          <div className="probability-value">
            집행유예 확률: {Math.round((sentence?.suspended_probability || 0.5) * 100)}%
          </div>
        </div>

        {/* 산정 근거 */}
        {sentence?.reasoning && (
          <div className="reasoning-section">
            <div className="reasoning-header">
              <FiInfo className="info-icon" />
              <span>이렇게 예상한 이유</span>
            </div>
            <p className="reasoning-text">{sentence.reasoning}</p>
          </div>
        )}

        {/* 용어 설명 */}
        <div className="terms-explanation">
          <div className="terms-header">
            <FiAlertCircle className="info-icon" />
            <span>용어 설명</span>
          </div>
          <ul className="terms-list">
            {punishmentTypes.map((item, idx) => (
              <li key={idx}>
                <strong>{item.type}</strong>: {item.desc}
              </li>
            ))}
          </ul>
        </div>

        {/* 주의사항 */}
        <div className="disclaimer">
          <p>
            * 이 예측은 AI가 유사 판례를 분석한 참고 자료입니다.
            <br />
            * 실제 결과는 재판 과정에서 달라질 수 있습니다.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ExpectedResultCard;
