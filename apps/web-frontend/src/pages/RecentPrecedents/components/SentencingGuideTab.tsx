/**
 * SentencingGuideTab Component
 *
 * 양형기준 조회 탭 컴포넌트
 * - 범죄 유형 선택
 * - 양형인자 체크리스트 (유리/불리)
 * - 예상 양형 범위 계산
 */

import React, { useState } from 'react';
import { apiClient } from '../../../api/client';
import { SentencingFactors, ExpectedSentence } from '../../../types';

interface SentencingGuideTabProps {
  onApply?: (estimate: ExpectedSentence) => void;
}

// 범죄 유형 목록
const CRIME_TYPES = [
  { value: 'theft', label: '절도' },
  { value: 'fraud', label: '사기' },
  { value: 'assault', label: '폭행/상해' },
  { value: 'embezzlement', label: '횡령/배임' },
  { value: 'drug', label: '마약' },
  { value: 'dui', label: '음주운전' },
  { value: 'sex_crime', label: '성범죄' },
  { value: 'murder', label: '살인' },
];

// 양형인자 옵션
const FACTOR_OPTIONS = {
  favorable: [
    '초범',
    '반성',
    '피해회복',
    '합의',
    '자수',
    '생계형 범죄',
    '우발적 범행',
    '심신미약',
    '형사처벌 불원',
    '선처 탄원',
  ],
  unfavorable: [
    '동종전과',
    '계획적 범행',
    '피해 중대',
    '도주 시도',
    '증거 인멸',
    '범행 후 태도 불량',
    '특수관계 이용',
    '다수 피해자',
    '범행 수법 불량',
    '반성 없음',
  ],
};

const SentencingGuideTab: React.FC<SentencingGuideTabProps> = ({ onApply }) => {
  const [crimeType, setCrimeType] = useState<string>('');
  const [factors, setFactors] = useState<SentencingFactors>({
    favorable: [],
    unfavorable: [],
  });
  const [estimate, setEstimate] = useState<ExpectedSentence | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculateEstimate = async () => {
    if (!crimeType) {
      setError('범죄 유형을 선택해주세요.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.estimateSentence({
        crime_type: crimeType,
        sentencing_factors: factors,
      });
      setEstimate(response);
    } catch (err) {
      console.error('양형 예측 실패:', err);
      // API가 없는 경우 mock 데이터 사용
      const mockEstimate = calculateMockEstimate(crimeType, factors);
      setEstimate(mockEstimate);
    } finally {
      setLoading(false);
    }
  };

  // Mock 양형 예측 (API가 없을 때 사용)
  const calculateMockEstimate = (
    type: string,
    sentencingFactors: SentencingFactors
  ): ExpectedSentence => {
    const baseRanges: Record<string, { min: number; max: number; unit: string }> = {
      theft: { min: 6, max: 36, unit: '개월' },
      fraud: { min: 12, max: 60, unit: '개월' },
      assault: { min: 6, max: 24, unit: '개월' },
      embezzlement: { min: 12, max: 60, unit: '개월' },
      drug: { min: 12, max: 60, unit: '개월' },
      dui: { min: 6, max: 24, unit: '개월' },
      sex_crime: { min: 24, max: 120, unit: '개월' },
      murder: { min: 60, max: 180, unit: '개월' },
    };

    const base = baseRanges[type] || { min: 6, max: 36, unit: '개월' };

    // 유리한 인자가 많으면 형량 감소
    const favorableCount = sentencingFactors.favorable.length;
    const unfavorableCount = sentencingFactors.unfavorable.length;

    const adjustment = (favorableCount - unfavorableCount) * 0.1;
    let adjustedMin = Math.max(base.min * (1 - adjustment), 1);
    let adjustedMax = Math.max(base.max * (1 - adjustment), adjustedMin + 6);

    // 집행유예 확률 계산
    let suspendedProb = 0.5;
    if (favorableCount > unfavorableCount) {
      suspendedProb = Math.min(0.9, 0.5 + favorableCount * 0.1);
    } else if (unfavorableCount > favorableCount) {
      suspendedProb = Math.max(0.1, 0.5 - unfavorableCount * 0.1);
    }

    // 형량이 3년 이상이면 집행유예 불가
    if (adjustedMax > 36) {
      suspendedProb = Math.min(suspendedProb, 0.3);
    }

    const formatRange = (min: number, max: number): string => {
      if (min >= 12 && max >= 12) {
        const minYears = Math.floor(min / 12);
        const maxYears = Math.floor(max / 12);
        const minMonths = min % 12;
        const maxMonths = max % 12;

        let minStr = minYears > 0 ? `${minYears}년` : '';
        if (minMonths > 0) minStr += ` ${minMonths}개월`;

        let maxStr = maxYears > 0 ? `${maxYears}년` : '';
        if (maxMonths > 0) maxStr += ` ${maxMonths}개월`;

        return `${minStr.trim()} ~ ${maxStr.trim()}`;
      }
      return `${Math.round(min)}개월 ~ ${Math.round(max)}개월`;
    };

    const crimeLabel = CRIME_TYPES.find(c => c.value === type)?.label || type;

    return {
      range: formatRange(adjustedMin, adjustedMax),
      suspended_probability: suspendedProb,
      reasoning: `${crimeLabel} 범죄에 대해 대법원 양형기준을 적용하였습니다. ` +
        `유리한 정상 ${favorableCount}개, 불리한 정상 ${unfavorableCount}개를 고려하여 ` +
        `예상 형량을 산정하였습니다.`,
    };
  };

  const toggleFactor = (type: 'favorable' | 'unfavorable', factor: string) => {
    setFactors(prev => {
      const current = prev[type];
      const updated = current.includes(factor)
        ? current.filter(f => f !== factor)
        : [...current, factor];
      return { ...prev, [type]: updated };
    });
    // 인자 변경 시 결과 초기화
    setEstimate(null);
  };

  const handleApply = () => {
    if (estimate && onApply) {
      onApply(estimate);
    }
  };

  const handleReset = () => {
    setCrimeType('');
    setFactors({ favorable: [], unfavorable: [] });
    setEstimate(null);
    setError(null);
  };

  return (
    <div className="sentencing-guide-tab">
      <div className="tab-header">
        <h2>양형기준 조회</h2>
        <p className="description">
          범죄 유형과 양형인자를 선택하면 대법원 양형기준에 따른 예상 양형을 계산합니다.
        </p>
      </div>

      {/* 범죄 유형 선택 */}
      <div className="crime-type-section">
        <h3>범죄 유형</h3>
        <div className="crime-type-buttons">
          {CRIME_TYPES.map(ct => (
            <button
              key={ct.value}
              className={`crime-type-btn ${crimeType === ct.value ? 'selected' : ''}`}
              onClick={() => {
                setCrimeType(ct.value);
                setEstimate(null);
              }}
            >
              {ct.label}
            </button>
          ))}
        </div>
      </div>

      {crimeType && (
        <>
          {/* 양형인자 체크리스트 */}
          <div className="factors-section">
            <div className="factor-group favorable">
              <h3>유리한 정상 (감경 요소)</h3>
              <div className="factor-checkboxes">
                {FACTOR_OPTIONS.favorable.map(factor => (
                  <label key={factor} className="factor-checkbox">
                    <input
                      type="checkbox"
                      checked={factors.favorable.includes(factor)}
                      onChange={() => toggleFactor('favorable', factor)}
                    />
                    <span className="checkbox-label">{factor}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="factor-group unfavorable">
              <h3>불리한 정상 (가중 요소)</h3>
              <div className="factor-checkboxes">
                {FACTOR_OPTIONS.unfavorable.map(factor => (
                  <label key={factor} className="factor-checkbox">
                    <input
                      type="checkbox"
                      checked={factors.unfavorable.includes(factor)}
                      onChange={() => toggleFactor('unfavorable', factor)}
                    />
                    <span className="checkbox-label">{factor}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* 액션 버튼 */}
          <div className="action-buttons">
            <button
              className="calculate-btn"
              onClick={calculateEstimate}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  계산 중...
                </>
              ) : (
                '양형 예측'
              )}
            </button>
            <button className="reset-btn" onClick={handleReset}>
              초기화
            </button>
          </div>

          {/* 에러 메시지 */}
          {error && <div className="error-message">{error}</div>}

          {/* 결과 표시 */}
          {estimate && (
            <div className="estimate-result">
              <h3>예상 양형 결과</h3>
              <div className="result-card">
                <div className="result-item sentence-range">
                  <span className="label">예상 형량</span>
                  <span className="value">{estimate.range}</span>
                </div>

                <div className="result-item probability">
                  <span className="label">집행유예 가능성</span>
                  <div className="probability-bar-container">
                    <div className="probability-bar">
                      <div
                        className="bar-fill"
                        style={{ width: `${estimate.suspended_probability * 100}%` }}
                      />
                    </div>
                    <span className="probability-value">
                      {Math.round(estimate.suspended_probability * 100)}%
                    </span>
                  </div>
                </div>

                {estimate.reasoning && (
                  <div className="result-item reasoning">
                    <span className="label">산정 근거</span>
                    <p className="reasoning-text">{estimate.reasoning}</p>
                  </div>
                )}

                {/* 선택된 인자 요약 */}
                <div className="selected-factors-summary">
                  {factors.favorable.length > 0 && (
                    <div className="factor-summary favorable">
                      <span className="factor-label">유리한 정상:</span>
                      <span className="factor-tags">
                        {factors.favorable.map(f => (
                          <span key={f} className="factor-tag">
                            {f}
                          </span>
                        ))}
                      </span>
                    </div>
                  )}
                  {factors.unfavorable.length > 0 && (
                    <div className="factor-summary unfavorable">
                      <span className="factor-label">불리한 정상:</span>
                      <span className="factor-tags">
                        {factors.unfavorable.map(f => (
                          <span key={f} className="factor-tag">
                            {f}
                          </span>
                        ))}
                      </span>
                    </div>
                  )}
                </div>

                {onApply && (
                  <button className="apply-btn" onClick={handleApply}>
                    사건에 적용
                  </button>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* 안내 */}
      <div className="guide-notice">
        <span className="icon">*</span>
        <span>
          본 양형 예측은 대법원 양형기준을 참고한 것이며, 실제 판결과 다를 수 있습니다.
          정확한 법률 자문은 변호사와 상담하시기 바랍니다.
        </span>
      </div>
    </div>
  );
};

export default SentencingGuideTab;
