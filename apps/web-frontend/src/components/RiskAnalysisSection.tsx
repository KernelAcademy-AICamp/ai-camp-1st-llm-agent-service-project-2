/**
 * Risk Analysis Section Component
 *
 * Displays risk analysis results for a document including:
 * - Overall risk score and severity
 * - Individual risk items by category
 * - Recommendations
 * - Summary
 */

import React, { useState, useEffect } from 'react';
import {
  RiskAnalysis,
  RiskItem,
  RiskSeverity,
  RiskCategory,
  RiskAnalysisResponse,
  AnalyzeRiskResponse
} from '../types';
import { apiClient } from '../api/client';
import '../styles/RiskAnalysisSection.css';

interface RiskAnalysisSectionProps {
  documentId: string;
  token?: string;
  documentTitle?: string;
}

const RiskAnalysisSection: React.FC<RiskAnalysisSectionProps> = ({
  documentId,
  token,
  documentTitle
}) => {
  const [riskAnalysis, setRiskAnalysis] = useState<RiskAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch existing risk analysis on mount
  useEffect(() => {
    fetchRiskAnalysis();
  }, [documentId]);

  const fetchRiskAnalysis = async () => {
    if (!documentId || !token) return;

    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getDocumentRiskAnalysis(documentId, token);
      if (response.risk_analysis) {
        setRiskAnalysis(response.risk_analysis);
      }
    } catch (err: any) {
      // If no risk analysis exists yet, that's okay
      console.log('No risk analysis found for document:', documentId);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeRisk = async () => {
    if (!documentId || !token) {
      setError('Authentication required');
      return;
    }

    setAnalyzing(true);
    setError(null);
    try {
      const response = await apiClient.analyzeDocumentRisk(documentId, token);
      if (response.success && response.risk_analysis) {
        setRiskAnalysis(response.risk_analysis);
      } else if (response.error) {
        setError(response.error);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to analyze risk');
    } finally {
      setAnalyzing(false);
    }
  };

  const getSeverityColor = (severity: RiskSeverity): string => {
    switch (severity) {
      case 'CRITICAL': return '#dc2626'; // red-600
      case 'HIGH': return '#ea580c'; // orange-600
      case 'MEDIUM': return '#ca8a04'; // yellow-600
      case 'LOW': return '#65a30d'; // lime-600
      case 'INFO': return '#0891b2'; // cyan-600
      default: return '#6b7280'; // gray-500
    }
  };

  const getSeverityLabel = (severity: RiskSeverity): string => {
    switch (severity) {
      case 'CRITICAL': return '심각';
      case 'HIGH': return '높음';
      case 'MEDIUM': return '중간';
      case 'LOW': return '낮음';
      case 'INFO': return '정보';
      default: return severity;
    }
  };

  const getCategoryLabel = (category: RiskCategory): string => {
    switch (category) {
      case 'LEGAL': return '법적 리스크';
      case 'FINANCIAL': return '재무 리스크';
      case 'COMPLIANCE': return '규정 준수';
      case 'OPERATIONAL': return '운영 리스크';
      case 'REPUTATIONAL': return '평판 리스크';
      case 'OTHER': return '기타';
      default: return category;
    }
  };

  const renderRiskScore = (score: number) => {
    const radius = 40;
    const strokeWidth = 8;
    const normalizedRadius = radius - strokeWidth / 2;
    const circumference = normalizedRadius * 2 * Math.PI;
    const strokeDashoffset = circumference - (score / 100) * circumference;

    let color = '#10b981'; // green
    if (score >= 70) color = '#dc2626'; // red
    else if (score >= 50) color = '#f59e0b'; // yellow
    else if (score >= 30) color = '#3b82f6'; // blue

    return (
      <div className="risk-score-circle">
        <svg height={radius * 2} width={radius * 2}>
          <circle
            stroke="#e5e7eb"
            fill="transparent"
            strokeWidth={strokeWidth}
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
          <circle
            stroke={color}
            fill="transparent"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference + ' ' + circumference}
            style={{ strokeDashoffset, transition: 'stroke-dashoffset 0.5s' }}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={radius}
            cy={radius}
            transform={`rotate(-90 ${radius} ${radius})`}
          />
        </svg>
        <div className="risk-score-text">
          <span className="risk-score-number">{score}</span>
          <span className="risk-score-label">점</span>
        </div>
      </div>
    );
  };

  const groupRiskItemsByCategory = (items: RiskItem[]): Record<RiskCategory, RiskItem[]> => {
    const grouped: Record<string, RiskItem[]> = {};
    items.forEach(item => {
      if (!grouped[item.category]) {
        grouped[item.category] = [];
      }
      grouped[item.category].push(item);
    });
    return grouped as Record<RiskCategory, RiskItem[]>;
  };

  if (loading) {
    return (
      <div className="risk-analysis-section">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>리스크 분석 정보를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (!riskAnalysis && !analyzing) {
    return (
      <div className="risk-analysis-section">
        <div className="risk-analysis-header">
          <h3>리스크 분석</h3>
        </div>
        <div className="no-analysis">
          <p>아직 리스크 분석이 수행되지 않았습니다.</p>
          <button
            onClick={handleAnalyzeRisk}
            className="analyze-button"
            disabled={analyzing}
          >
            리스크 분석 시작
          </button>
        </div>
        {error && <div className="error-message">{error}</div>}
      </div>
    );
  }

  if (analyzing) {
    return (
      <div className="risk-analysis-section">
        <div className="analyzing-container">
          <div className="spinner"></div>
          <p>문서 리스크를 분석하는 중입니다...</p>
          <p className="analyzing-hint">이 작업은 1-2분 정도 소요될 수 있습니다.</p>
        </div>
      </div>
    );
  }

  if (!riskAnalysis) return null;

  const groupedRisks = groupRiskItemsByCategory(riskAnalysis.risk_items);

  return (
    <div className="risk-analysis-section">
      <div className="risk-analysis-header">
        <h3>리스크 분석</h3>
        <span className="analysis-date">
          분석일: {new Date(riskAnalysis.created_at).toLocaleDateString('ko-KR')}
        </span>
      </div>

      {/* Overall Risk Score */}
      <div className="risk-overview">
        <div className="risk-score-container">
          {renderRiskScore(riskAnalysis.overall_risk_score)}
          <div className="risk-severity">
            <span
              className="severity-badge"
              style={{ backgroundColor: getSeverityColor(riskAnalysis.severity) }}
            >
              {getSeverityLabel(riskAnalysis.severity)}
            </span>
          </div>
        </div>
        <div className="risk-summary">
          <h4>리스크 요약</h4>
          <p>{riskAnalysis.summary}</p>
        </div>
      </div>

      {/* Risk Items by Category */}
      <div className="risk-items-container">
        <h4>리스크 항목 ({riskAnalysis.risk_items.length}개)</h4>
        {Object.entries(groupedRisks).map(([category, items]) => (
          <div key={category} className="risk-category-section">
            <h5 className="risk-category-title">
              {getCategoryLabel(category as RiskCategory)} ({items.length})
            </h5>
            <div className="risk-items">
              {items.map((item, index) => (
                <div key={index} className="risk-item">
                  <div className="risk-item-header">
                    <span className="risk-item-title">{item.title}</span>
                    <span
                      className="risk-item-severity"
                      style={{ color: getSeverityColor(item.severity) }}
                    >
                      {getSeverityLabel(item.severity)} ({item.score}점)
                    </span>
                  </div>
                  <p className="risk-item-description">{item.description}</p>
                  {item.clause_reference && (
                    <p className="risk-item-reference">
                      관련 조항: {item.clause_reference}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Recommendations */}
      {riskAnalysis.recommendations && riskAnalysis.recommendations.length > 0 && (
        <div className="risk-recommendations">
          <h4>권장 사항</h4>
          <ul>
            {riskAnalysis.recommendations.map((rec, index) => (
              <li key={index}>{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Refresh Analysis Button */}
      <div className="risk-actions">
        <button
          onClick={handleAnalyzeRisk}
          className="refresh-analysis-button"
          disabled={analyzing}
        >
          리스크 재분석
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default RiskAnalysisSection;