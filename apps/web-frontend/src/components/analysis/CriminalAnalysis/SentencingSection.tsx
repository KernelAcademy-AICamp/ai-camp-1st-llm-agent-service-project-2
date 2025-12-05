import React, { useState, useEffect, useCallback } from 'react';
import { FiThumbsUp, FiThumbsDown, FiBarChart2, FiActivity, FiInfo, FiRefreshCw } from 'react-icons/fi';
import { SentencingFactors, ExpectedSentence } from '../../../types';
import { apiClient } from '../../../api/client';
import './CriminalAnalysis.css';

interface SentencingSectionProps {
  documentId: string;
  token?: string;
  // Pre-loaded data (optional)
  initialFactors?: SentencingFactors;
  initialSentence?: ExpectedSentence;
}

const SentencingSection: React.FC<SentencingSectionProps> = ({
  documentId,
  token,
  initialFactors,
  initialSentence
}) => {
  const [factors, setFactors] = useState<SentencingFactors | null>(initialFactors || null);
  const [sentence, setSentence] = useState<ExpectedSentence | null>(initialSentence || null);
  const [loading, setLoading] = useState(!initialFactors && !initialSentence);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const loadSentencingData = useCallback(async () => {
    if (!documentId || !token) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getCriminalAnalysis(documentId, token);
      if (response.sentencing_factors) {
        setFactors(response.sentencing_factors);
      }
      if (response.expected_sentence) {
        setSentence(response.expected_sentence);
      }
    } catch (err: any) {
      console.log('No sentencing data found for document:', documentId);
    } finally {
      setLoading(false);
    }
  }, [documentId, token]);

  useEffect(() => {
    if (!initialFactors && !initialSentence) {
      loadSentencingData();
    }
  }, [loadSentencingData, initialFactors, initialSentence]);

  const handleAnalyze = async () => {
    if (!documentId || !token) return;

    setAnalyzing(true);
    setError(null);

    try {
      const response = await apiClient.analyzeCriminalDocument(documentId, token);
      if (response.sentencing_factors) {
        setFactors(response.sentencing_factors);
      }
      if (response.expected_sentence) {
        setSentence(response.expected_sentence);
      }
    } catch (err: any) {
      setError(err.message || '양형 분석에 실패했습니다.');
    } finally {
      setAnalyzing(false);
    }
  };

  // 집행유예 가능성에 따른 색상 결정
  const getProbabilityColor = (prob: number) => {
    if (prob >= 70) return '#10b981'; // 녹색 (높음)
    if (prob >= 40) return '#f59e0b'; // 주황색 (보통)
    return '#ef4444'; // 빨간색 (낮음)
  };

  if (loading) {
    return (
      <div className="criminal-section sentencing-section">
        <div className="section-header">
          <div className="section-title">
            <FiBarChart2 className="section-icon" />
            <h3>양형 분석</h3>
          </div>
        </div>
        <div className="section-content">
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>양형 분석 데이터를 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!factors && !sentence) {
    return (
      <div className="criminal-section sentencing-section">
        <div className="section-header">
          <div className="section-title">
            <FiBarChart2 className="section-icon" />
            <h3>양형 분석</h3>
          </div>
        </div>
        <div className="section-content">
          <div className="empty-state">
            <FiBarChart2 className="empty-icon" />
            <p>아직 양형 분석이 수행되지 않았습니다.</p>
            <button
              className="btn-analyze"
              onClick={handleAnalyze}
              disabled={analyzing}
            >
              {analyzing ? (
                <>
                  <FiRefreshCw className="icon-spin" />
                  분석 중...
                </>
              ) : (
                '양형 분석하기'
              )}
            </button>
            {error && <p className="error-message">{error}</p>}
          </div>
        </div>
      </div>
    );
  }

  const probabilityPercent = sentence ? Math.round(sentence.suspended_probability * 100) : 0;
  const probabilityColor = getProbabilityColor(probabilityPercent);

  return (
    <div className="criminal-section sentencing-section">
      <div className="section-header">
        <div className="section-title">
          <FiBarChart2 className="section-icon" />
          <h3>양형 분석</h3>
        </div>
      </div>

      <div className="section-content">
        {/* 양형인자 */}
        {factors && (
          <div className="sentencing-factors">
            <div className="factors-grid">
              {/* 유리한 정상 */}
              <div className="factor-group favorable">
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
              <div className="factor-group unfavorable">
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
        )}

        {/* 예상 양형 */}
        {sentence && (
          <div className="sentence-estimate">
            <div className="estimate-header">
              <FiActivity className="estimate-icon" />
              <h4>양형 예측</h4>
            </div>

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
        )}

        <button
          className="btn-refresh"
          onClick={handleAnalyze}
          disabled={analyzing}
        >
          {analyzing ? (
            <>
              <FiRefreshCw className="icon-spin" />
              재분석 중...
            </>
          ) : (
            <>
              <FiRefreshCw />
              재분석
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default SentencingSection;
