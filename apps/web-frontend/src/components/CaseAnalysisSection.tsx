/**
 * Case Analysis Section Component
 *
 * Displays case analysis results for a document including:
 * - Case name and summary
 * - Parties and key dates
 * - Issues and related precedents
 * - Suggested next steps
 */

import React, { useState, useEffect } from 'react';
import { FiFolder, FiUsers, FiCalendar, FiAlertCircle, FiBookOpen, FiArrowRight, FiCpu, FiRefreshCw } from 'react-icons/fi';
import {
  DocumentCaseAnalysis,
  CaseAnalysisResponse,
  AnalyzeCaseRequest,
  AnalyzeCaseResponse
} from '../types';
import { apiClient } from '../api/client';
import '../styles/CaseAnalysisSection.css';

interface CaseAnalysisSectionProps {
  documentId: string;
  token?: string;
  documentTitle?: string;
}

const CaseAnalysisSection: React.FC<CaseAnalysisSectionProps> = ({
  documentId,
  token,
  documentTitle
}) => {
  const [caseAnalysis, setCaseAnalysis] = useState<DocumentCaseAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);
  const [selectedScenario, setSelectedScenario] = useState<string>('소송 준비');

  // Fetch existing case analysis on mount
  useEffect(() => {
    fetchCaseAnalysis();
  }, [documentId]);

  const fetchCaseAnalysis = async () => {
    if (!documentId || !token) return;

    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getCaseAnalysis(documentId, token);
      if (response.case_analysis) {
        setCaseAnalysis(response.case_analysis);
      }
    } catch (err: any) {
      // If no case analysis exists yet, that's okay
      console.log('No case analysis found for document:', documentId);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeCase = async () => {
    if (!documentId || !token) {
      setError('Authentication required');
      return;
    }

    setAnalyzing(true);
    setError(null);
    try {
      const request: AnalyzeCaseRequest = {
        scenario: selectedScenario as '소송 준비' | '계약 검토' | '법적 자문' | '기타'
      };

      const response = await apiClient.analyzeCase(documentId, request, token);
      if (response.success && response.case_analysis) {
        setCaseAnalysis(response.case_analysis);
      } else if (response.error) {
        setError(response.error);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to analyze case');
    } finally {
      setAnalyzing(false);
    }
  };

  const scenarios = [
    { value: '소송 준비', label: '소송 준비', icon: '⚖️' },
    { value: '계약 검토', label: '계약 검토', icon: '📝' },
    { value: '법적 자문', label: '법적 자문', icon: '💡' },
    { value: '기타', label: '기타', icon: '📋' }
  ];

  if (loading) {
    return (
      <div className="case-analysis-section">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>사건 분석 정보를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (!caseAnalysis && !analyzing) {
    return (
      <div className="case-analysis-section">
        <div className="case-analysis-header">
          <h3><FiFolder /> 사건 분석</h3>
        </div>
        <div className="no-analysis">
          <p>아직 사건 분석이 수행되지 않았습니다.</p>
          <div className="scenario-selector">
            <label>분석 시나리오 선택:</label>
            <div className="scenario-buttons">
              {scenarios.map(scenario => (
                <button
                  key={scenario.value}
                  className={`scenario-btn ${selectedScenario === scenario.value ? 'active' : ''}`}
                  onClick={() => setSelectedScenario(scenario.value)}
                >
                  <span className="scenario-icon">{scenario.icon}</span>
                  {scenario.label}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={handleAnalyzeCase}
            className="analyze-button"
            disabled={analyzing}
          >
            <FiCpu /> 사건 분석 시작
          </button>
        </div>
        {error && <div className="error-message">{error}</div>}
      </div>
    );
  }

  if (analyzing) {
    return (
      <div className="case-analysis-section">
        <div className="analyzing-container">
          <div className="spinner"></div>
          <p>문서를 사건으로 분석하는 중입니다...</p>
          <p className="analyzing-hint">이 작업은 1-2분 정도 소요될 수 있습니다.</p>
        </div>
      </div>
    );
  }

  if (!caseAnalysis) return null;

  return (
    <div className="case-analysis-section">
      <div className="case-analysis-header">
        <h3 onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer' }}>
          {expanded ? '▼' : '▶'} <FiFolder /> 사건 분석
        </h3>
        <span className="analysis-date">
          분석일: {new Date(caseAnalysis.created_at).toLocaleDateString('ko-KR')}
        </span>
      </div>

      {expanded && (
        <>
          {/* Case Overview */}
          <div className="case-overview">
            <div className="case-name">
              <h4>{caseAnalysis.suggested_case_name}</h4>
              {caseAnalysis.scenario && (
                <span className="case-scenario-badge">
                  {scenarios.find(s => s.value === caseAnalysis.scenario)?.icon} {caseAnalysis.scenario}
                </span>
              )}
            </div>

            <div className="case-meta">
              <div className="meta-item">
                <FiUsers />
                <span>{caseAnalysis.party_count || Object.keys(caseAnalysis.parties || {}).length}개 당사자</span>
              </div>
              <div className="meta-item">
                <FiCalendar />
                <span>{Object.keys(caseAnalysis.key_dates || {}).length}개 주요 날짜</span>
              </div>
              <div className="meta-item">
                <FiAlertCircle />
                <span>{caseAnalysis.issue_count || caseAnalysis.issues.length}개 쟁점</span>
              </div>
              {caseAnalysis.has_precedents && (
                <div className="meta-item">
                  <FiBookOpen />
                  <span>관련 판례 있음</span>
                </div>
              )}
            </div>
          </div>

          {/* Document Types */}
          {caseAnalysis.document_types && caseAnalysis.document_types.length > 0 && (
            <div className="case-section">
              <h4>문서 유형</h4>
              <div className="tag-list">
                {caseAnalysis.document_types.map((type, idx) => (
                  <span key={idx} className="tag">{type}</span>
                ))}
              </div>
            </div>
          )}

          {/* Parties */}
          {caseAnalysis.parties && Object.keys(caseAnalysis.parties).length > 0 && (
            <div className="case-section">
              <h4><FiUsers /> 당사자</h4>
              <div className="parties-list">
                {Object.entries(caseAnalysis.parties).map(([role, name]) => (
                  <div key={role} className="party-item">
                    <span className="party-role">{role}:</span>
                    <span className="party-name">{name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Key Dates */}
          {caseAnalysis.key_dates && Object.keys(caseAnalysis.key_dates).length > 0 && (
            <div className="case-section">
              <h4><FiCalendar /> 주요 날짜</h4>
              <div className="dates-list">
                {Object.entries(caseAnalysis.key_dates).map(([label, date]) => (
                  <div key={label} className="date-item">
                    <span className="date-label">{label}:</span>
                    <span className="date-value">{date}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Issues */}
          {caseAnalysis.issues && caseAnalysis.issues.length > 0 && (
            <div className="case-section">
              <h4><FiAlertCircle /> 주요 쟁점</h4>
              <ul className="issues-list">
                {caseAnalysis.issues.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Related Precedents */}
          {caseAnalysis.related_precedents && caseAnalysis.related_precedents.length > 0 && (
            <div className="case-section">
              <h4><FiBookOpen /> 관련 판례</h4>
              <ul className="precedents-list">
                {caseAnalysis.related_precedents.map((precedent, idx) => (
                  <li key={idx}>{precedent}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested Next Steps */}
          {caseAnalysis.suggested_next_steps && caseAnalysis.suggested_next_steps.length > 0 && (
            <div className="case-section next-steps">
              <h4><FiArrowRight /> 다음 단계 제안</h4>
              <ul className="steps-list">
                {caseAnalysis.suggested_next_steps.map((step, idx) => (
                  <li key={idx}>
                    <span className="step-number">{idx + 1}</span>
                    {step}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Refresh Analysis Button */}
          <div className="case-actions">
            <button
              onClick={handleAnalyzeCase}
              className="refresh-analysis-button"
              disabled={analyzing}
            >
              <FiRefreshCw /> 사건 재분석
            </button>
          </div>

          {error && <div className="error-message">{error}</div>}
        </>
      )}
    </div>
  );
};

export default CaseAnalysisSection;