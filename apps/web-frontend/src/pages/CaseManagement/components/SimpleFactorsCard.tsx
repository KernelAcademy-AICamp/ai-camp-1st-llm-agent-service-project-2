import React from 'react';
import { FiThumbsUp, FiThumbsDown } from 'react-icons/fi';
import { SentencingFactors } from '../../../types';
import './SimpleCards.css';

interface SimpleFactorsCardProps {
  factors: SentencingFactors;
  role?: 'victim' | 'defendant'; // 피해자 vs 피의자 관점
}

// 전문 용어 -> 쉬운 용어 매핑
const simplifyFactor = (factor: string): string => {
  const mappings: Record<string, string> = {
    '초범': '처음 저지른 잘못',
    '반성': '잘못을 뉘우침',
    '피해회복': '피해를 보상함',
    '피해 회복': '피해를 보상함',
    '합의': '피해자와 합의함',
    '자수': '스스로 신고함',
    '자백': '잘못을 인정함',
    '우발적 범행': '순간적으로 저지른 행동',
    '우발': '순간적인 실수',
    '고령': '나이가 많음',
    '질병': '건강이 안 좋음',
    '건강문제': '건강상 문제가 있음',
    '동종전과': '같은 종류의 전과가 있음',
    '동종 전과': '같은 종류의 전과가 있음',
    '이종전과': '다른 종류의 전과가 있음',
    '이종 전과': '다른 종류의 전과가 있음',
    '전과': '이전에 처벌받은 적 있음',
    '계획적 범행': '미리 계획하고 저지름',
    '계획범행': '미리 계획하고 저지름',
    '조직적 범행': '여러 명이 함께 저지름',
    '상습': '반복적으로 저지름',
    '상습범': '반복적으로 저지름',
    '피해 중대': '피해가 심각함',
    '중대 피해': '피해가 심각함',
    '반성 없음': '잘못을 인정하지 않음',
  };

  // 매핑된 용어가 있으면 변환, 없으면 원본 반환
  for (const [key, value] of Object.entries(mappings)) {
    if (factor.toLowerCase().includes(key.toLowerCase())) {
      return value;
    }
  }
  return factor;
};

const SimpleFactorsCard: React.FC<SimpleFactorsCardProps> = ({ factors, role = 'victim' }) => {
  const favorable = factors?.favorable || [];
  const unfavorable = factors?.unfavorable || [];

  // 피해자 관점이면 라벨 변경
  const favorableLabel = role === 'victim' ? '상대방에게 불리한 점' : '유리한 점';
  const unfavorableLabel = role === 'victim' ? '상대방에게 유리한 점' : '불리한 점';

  const favorableDescription =
    role === 'victim'
      ? '이런 점들이 있으면 상대방이 더 무거운 처벌을 받을 수 있어요.'
      : '이런 점들이 있으면 처벌이 가벼워질 수 있어요.';

  const unfavorableDescription =
    role === 'victim'
      ? '이런 점들이 있으면 상대방이 가벼운 처벌을 받을 수 있어요.'
      : '이런 점들이 있으면 처벌이 무거워질 수 있어요.';

  return (
    <div className="simple-card factors-card">
      <div className="card-header">
        <h4>유리한 점 / 불리한 점</h4>
        <span className="card-subtitle">
          {role === 'victim' ? '(피해자 관점)' : '(피의자 관점)'}
        </span>
      </div>

      <div className="factors-content">
        {/* 유리한 점 (피해자 관점에선 상대방에게 불리한 점) */}
        <div className="factor-section favorable">
          <div className="factor-header">
            <FiThumbsUp className="factor-icon favorable" />
            <h5>{favorableLabel}</h5>
          </div>
          <p className="factor-description">{favorableDescription}</p>

          {favorable.length > 0 ? (
            <ul className="factor-list">
              {favorable.map((factor, idx) => (
                <li key={idx} className="factor-item favorable">
                  <span className="bullet">+</span>
                  <span className="text">{simplifyFactor(factor)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="no-factors">해당 사항 없음</p>
          )}
        </div>

        {/* 불리한 점 (피해자 관점에선 상대방에게 유리한 점) */}
        <div className="factor-section unfavorable">
          <div className="factor-header">
            <FiThumbsDown className="factor-icon unfavorable" />
            <h5>{unfavorableLabel}</h5>
          </div>
          <p className="factor-description">{unfavorableDescription}</p>

          {unfavorable.length > 0 ? (
            <ul className="factor-list">
              {unfavorable.map((factor, idx) => (
                <li key={idx} className="factor-item unfavorable">
                  <span className="bullet">-</span>
                  <span className="text">{simplifyFactor(factor)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="no-factors">해당 사항 없음</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default SimpleFactorsCard;
