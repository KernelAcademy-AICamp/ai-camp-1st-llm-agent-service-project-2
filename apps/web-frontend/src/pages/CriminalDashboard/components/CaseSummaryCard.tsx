import React from 'react';
import { CriminalCase, CRIMINAL_STAGE_LABELS } from '../../../types';
import { FiFileText, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';

interface CaseSummaryCardProps {
  caseData: CriminalCase | null;
}

const CaseSummaryCard: React.FC<CaseSummaryCardProps> = ({ caseData }) => {
  if (!caseData) {
    return (
      <div className="case-summary-card empty">
        <div className="empty-state">
          <FiFileText className="empty-icon" />
          <p>등록된 사건이 없습니다.</p>
        </div>
      </div>
    );
  }

  const {
    case_name,
    crime_type,
    expected_sentence,
    sentencing_factors,
    stage
  } = caseData;

  // 집행유예 가능성 퍼센트
  const suspendedProbability = expected_sentence?.suspended_probability
    ? Math.round(expected_sentence.suspended_probability * 100)
    : 0;

  return (
    <div className="case-summary-card">
      <h4 className="card-title">내 사건 요약</h4>

      <div className="case-info">
        <div className="crime-type-badge large">
          {crime_type || '미분류'}
        </div>
        <h5 className="case-name">{case_name}</h5>
        {stage && (
          <span className="stage-badge">
            {CRIMINAL_STAGE_LABELS[stage]}
          </span>
        )}
      </div>

      {/* 예상 결과 */}
      {expected_sentence && (
        <div className="expected-result">
          <h5>예상 결과</h5>
          <div className="probability-bar">
            <div
              className="probability-fill"
              style={{ width: `${suspendedProbability}%` }}
            />
            <span className="probability-text">
              집행유예 가능성 {suspendedProbability}%
            </span>
          </div>
          {expected_sentence.range && (
            <p className="sentence-range">
              예상 형량: <strong>{expected_sentence.range}</strong>
            </p>
          )}
        </div>
      )}

      {/* 양형인자 요약 */}
      {sentencing_factors && (
        <div className="factors-summary">
          {sentencing_factors.favorable.length > 0 && (
            <div className="factor-group favorable">
              <FiCheckCircle className="factor-icon" />
              <span>유리한 점: {sentencing_factors.favorable.slice(0, 3).join(', ')}</span>
            </div>
          )}
          {sentencing_factors.unfavorable.length > 0 && (
            <div className="factor-group unfavorable">
              <FiAlertCircle className="factor-icon" />
              <span>불리한 점: {sentencing_factors.unfavorable.slice(0, 3).join(', ')}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CaseSummaryCard;
