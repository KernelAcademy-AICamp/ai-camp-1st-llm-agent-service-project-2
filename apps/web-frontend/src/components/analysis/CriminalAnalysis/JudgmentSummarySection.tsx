import React, { useState, useEffect, useCallback } from 'react';
import { FiFileText, FiRefreshCw, FiCalendar, FiMapPin, FiUser, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';
import { apiClient } from '../../../api/client';
import './CriminalAnalysis.css';

interface JudgmentInfo {
  case_number?: string;
  court?: string;
  judge?: string;
  decision_date?: string;
  decision_type?: string;  // 유죄/무죄/일부유죄
  charges?: string[];
  verdict?: string;
}

interface JudgmentSummary {
  main_issue?: string;       // 주요 쟁점
  facts?: string;            // 사실관계
  court_reasoning?: string;  // 법원 판단
  key_points?: string[];     // 판시사항 핵심
  legal_principles?: string[]; // 적용 법리
  info?: JudgmentInfo;
}

interface JudgmentSummarySectionProps {
  documentId: string;
  token?: string;
  // Pre-loaded data (optional)
  initialSummary?: JudgmentSummary;
}

const JudgmentSummarySection: React.FC<JudgmentSummarySectionProps> = ({
  documentId,
  token,
  initialSummary
}) => {
  const [summary, setSummary] = useState<JudgmentSummary | null>(initialSummary || null);
  const [loading, setLoading] = useState(!initialSummary);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [expanded, setExpanded] = useState<{ [key: string]: boolean }>({
    facts: false,
    reasoning: false
  });

  const loadSummary = useCallback(async () => {
    if (!documentId || !token) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getCriminalAnalysis(documentId, token);
      if (response.judgment_summary) {
        setSummary(response.judgment_summary);
      }
    } catch (err: any) {
      console.log('No judgment summary found for document:', documentId);
    } finally {
      setLoading(false);
    }
  }, [documentId, token]);

  useEffect(() => {
    if (!initialSummary) {
      loadSummary();
    }
  }, [loadSummary, initialSummary]);

  const handleAnalyze = async () => {
    if (!documentId || !token) return;

    setAnalyzing(true);
    setError(null);

    try {
      const response = await apiClient.analyzeCriminalDocument(documentId, token);
      if (response.judgment_summary) {
        setSummary(response.judgment_summary);
      }
    } catch (err: any) {
      setError(err.message || '판시사항 분석에 실패했습니다.');
    } finally {
      setAnalyzing(false);
    }
  };

  const toggleExpand = (section: string) => {
    setExpanded(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const truncateText = (text: string, maxLength: number = 200) => {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + '...';
  };

  if (loading) {
    return (
      <div className="criminal-section judgment-summary-section">
        <div className="section-header">
          <div className="section-title">
            <FiFileText className="section-icon" />
            <h3>판시사항 요약</h3>
          </div>
        </div>
        <div className="section-content">
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>판시사항 요약 데이터를 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="criminal-section judgment-summary-section">
        <div className="section-header">
          <div className="section-title">
            <FiFileText className="section-icon" />
            <h3>판시사항 요약</h3>
          </div>
        </div>
        <div className="section-content">
          <div className="empty-state">
            <FiFileText className="empty-icon" />
            <p>아직 판시사항 분석이 수행되지 않았습니다.</p>
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
                '판시사항 분석하기'
              )}
            </button>
            {error && <p className="error-message">{error}</p>}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="criminal-section judgment-summary-section">
      <div className="section-header">
        <div className="section-title">
          <FiFileText className="section-icon" />
          <h3>판시사항 요약</h3>
        </div>
        {summary.info?.decision_type && (
          <div className={`decision-badge ${summary.info.decision_type === '무죄' ? 'acquittal' : 'guilty'}`}>
            {summary.info.decision_type === '무죄' ? <FiCheckCircle /> : <FiAlertCircle />}
            <span>{summary.info.decision_type}</span>
          </div>
        )}
      </div>

      <div className="section-content">
        {/* 사건 정보 */}
        {summary.info && (
          <div className="judgment-info">
            {summary.info.case_number && (
              <span className="info-item">
                <FiFileText />
                {summary.info.case_number}
              </span>
            )}
            {summary.info.court && (
              <span className="info-item">
                <FiMapPin />
                {summary.info.court}
              </span>
            )}
            {summary.info.decision_date && (
              <span className="info-item">
                <FiCalendar />
                {summary.info.decision_date}
              </span>
            )}
            {summary.info.judge && (
              <span className="info-item">
                <FiUser />
                {summary.info.judge}
              </span>
            )}
          </div>
        )}

        {/* 혐의 */}
        {summary.info?.charges && summary.info.charges.length > 0 && (
          <div className="charges-section">
            <h4>혐의</h4>
            <div className="charges-list">
              {summary.info.charges.map((charge, idx) => (
                <span key={idx} className="charge-tag">{charge}</span>
              ))}
            </div>
          </div>
        )}

        {/* 주요 쟁점 */}
        {summary.main_issue && (
          <div className="summary-block main-issue">
            <h4>주요 쟁점</h4>
            <p>{summary.main_issue}</p>
          </div>
        )}

        {/* 사실관계 */}
        {summary.facts && (
          <div className="summary-block facts">
            <h4>사실관계</h4>
            <p>
              {expanded.facts ? summary.facts : truncateText(summary.facts)}
            </p>
            {summary.facts.length > 200 && (
              <button className="btn-expand" onClick={() => toggleExpand('facts')}>
                {expanded.facts ? '접기' : '더 보기'}
              </button>
            )}
          </div>
        )}

        {/* 법원 판단 */}
        {summary.court_reasoning && (
          <div className="summary-block court-reasoning">
            <h4>법원 판단</h4>
            <p>
              {expanded.reasoning ? summary.court_reasoning : truncateText(summary.court_reasoning)}
            </p>
            {summary.court_reasoning.length > 200 && (
              <button className="btn-expand" onClick={() => toggleExpand('reasoning')}>
                {expanded.reasoning ? '접기' : '더 보기'}
              </button>
            )}
          </div>
        )}

        {/* 판시사항 핵심 */}
        {summary.key_points && summary.key_points.length > 0 && (
          <div className="key-points">
            <h4>핵심 판시사항</h4>
            <ul>
              {summary.key_points.map((point, idx) => (
                <li key={idx}>{point}</li>
              ))}
            </ul>
          </div>
        )}

        {/* 적용 법리 */}
        {summary.legal_principles && summary.legal_principles.length > 0 && (
          <div className="legal-principles">
            <h4>적용 법리</h4>
            <div className="principles-list">
              {summary.legal_principles.map((principle, idx) => (
                <span key={idx} className="principle-tag">{principle}</span>
              ))}
            </div>
          </div>
        )}

        {/* 선고 */}
        {summary.info?.verdict && (
          <div className="verdict-section">
            <h4>선고</h4>
            <div className="verdict-content">
              {summary.info.verdict}
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

export default JudgmentSummarySection;
