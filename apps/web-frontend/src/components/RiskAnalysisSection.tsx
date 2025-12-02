/**
 * Risk Analysis Section Component
 *
 * Displays risk analysis results for a document including:
 * - Overall risk score and severity
 * - Individual risk items by category
 * - Recommendations
 * - Summary
 * - Model selection and comparison
 */

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  RiskAnalysis,
  RiskItem,
  RiskSeverity,
  RiskCategory,
  RiskAnalysisResponse,
  AnalyzeRiskResponse,
  AnalysisStatus
} from '../types';
import { apiClient } from '../api/client';
import ModelSelector from './ModelSelector';
import '../styles/RiskAnalysisSection.css';

// 모델별 리스크 분석 결과를 저장하는 타입
interface ModelRiskResult {
  modelId: string;
  modelName: string;
  provider: string;
  riskAnalysis: RiskAnalysis;
  timestamp: string;
  processingTime?: number;
  isLatest?: boolean;
}

interface RiskAnalysisSectionProps {
  documentId: string;
  token?: string;
  documentTitle?: string;
  analysisStatus?: AnalysisStatus;
}

const RiskAnalysisSection: React.FC<RiskAnalysisSectionProps> = ({
  documentId,
  token,
  documentTitle,
  analysisStatus
}) => {
  const [riskAnalysis, setRiskAnalysis] = useState<RiskAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Model selection state
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [selectedModelName, setSelectedModelName] = useState<string>('');
  const [analyzingWithModel, setAnalyzingWithModel] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);

  // Comparison results - store multiple model results
  const [comparisonResults, setComparisonResults] = useState<ModelRiskResult[]>([]);
  const [showComparison, setShowComparison] = useState(false);

  // Helper to guess provider from model name
  const getProviderFromModel = (modelName: string): string => {
    const name = modelName.toLowerCase();
    if (name.includes('gpt') || name.includes('openai')) return 'openai';
    if (name.includes('claude') || name.includes('anthropic')) return 'anthropic';
    if (name.includes('gemini') || name.includes('google')) return 'google';
    if (name.includes('ollama') || name.includes('local')) return 'ollama';
    return 'openai';
  };

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
        // Add to comparison results
        addToComparisonResults(response.risk_analysis, 'default');
      } else if (response.error) {
        setError(response.error);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to analyze risk');
    } finally {
      setAnalyzing(false);
    }
  };

  // Add result to comparison list
  const addToComparisonResults = (analysis: RiskAnalysis, modelId: string, modelName?: string, processingTime?: number) => {
    const newResult: ModelRiskResult = {
      modelId,
      modelName: modelName || modelId,
      provider: getProviderFromModel(modelName || modelId),
      riskAnalysis: analysis,
      timestamp: analysis.created_at,
      processingTime,
      isLatest: true,
    };

    setComparisonResults(prev => {
      // Check if this model already has a result
      const existingIndex = prev.findIndex(r => r.modelId === modelId);
      if (existingIndex !== -1) {
        // Update existing result
        const updated = [...prev];
        updated[existingIndex] = { ...newResult, isLatest: true };
        return updated.map((r, i) => ({ ...r, isLatest: i === existingIndex }));
      }
      // Add new result and mark as latest
      return [
        ...prev.map(r => ({ ...r, isLatest: false })),
        newResult,
      ];
    });
  };

  const handleModelSelect = (modelId: string, modelName: string) => {
    setSelectedModelId(modelId);
    setSelectedModelName(modelName);
    setModelError(null);
  };

  const handleAnalyzeWithModel = async () => {
    if (!documentId || !token || !selectedModelId) return;

    setAnalyzingWithModel(true);
    setModelError(null);

    try {
      const response = await apiClient.analyzeRiskWithModel(
        documentId,
        selectedModelId,
        token
      );

      if (response.success && response.risk_analysis) {
        // Add to comparison results
        addToComparisonResults(
          response.risk_analysis,
          selectedModelId,
          response.model_used || selectedModelName,
          response.processing_time_ms
        );
        setShowComparison(true);
      } else if (response.error) {
        setModelError(response.error);
      }
    } catch (err: any) {
      console.error('Failed to analyze risk with model:', err);
      setModelError(err.message || '리스크 분석에 실패했습니다.');
    } finally {
      setAnalyzingWithModel(false);
    }
  };

  const handleRemoveComparisonResult = (modelId: string) => {
    setComparisonResults(prev => prev.filter(r => r.modelId !== modelId));
    if (comparisonResults.length <= 2) {
      setShowComparison(false);
    }
  };

  const handleClearComparison = () => {
    const latestResult = comparisonResults.find(r => r.isLatest);
    if (latestResult) {
      setComparisonResults([latestResult]);
    }
    setShowComparison(false);
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

  // 심각도별 리스크 개수 계산
  const countBySeverity = (items: RiskItem[]) => {
    const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
    items.forEach(item => {
      if (counts.hasOwnProperty(item.severity)) {
        counts[item.severity as keyof typeof counts]++;
      }
    });
    return counts;
  };

  // Check if risk analysis is currently in progress
  const isAnalyzingRisk = analysisStatus === 'analyzing_risk';

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

  // Show analysis in progress banner when analyzing_risk
  if (isAnalyzingRisk) {
    return (
      <div className="risk-analysis-section">
        <div className="risk-analysis-header">
          <h3>리스크 분석</h3>
        </div>
        <div className="analysis-in-progress-banner">
          <div className="analysis-spinner"></div>
          <div className="analysis-info">
            <span className="analysis-step-badge">3/3</span>
            <span className="analysis-label">리스크 분석 중...</span>
          </div>
          <p className="analysis-hint">문서의 법적 리스크를 분석하고 있습니다. 잠시만 기다려 주세요.</p>
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
  const severityCounts = countBySeverity(riskAnalysis.risk_items);

  return (
    <div className="risk-analysis-section">
      <div className="risk-analysis-header">
        <h3>리스크 분석</h3>
        <span className="analysis-date">
          분석일: {new Date(riskAnalysis.created_at).toLocaleDateString('ko-KR')}
        </span>
      </div>

      {/* Risk Statistics Cards */}
      <div className="risk-stats-grid">
        <div className="risk-stat-card risk-stat-score">
          <div className="stat-icon">
            {renderRiskScore(riskAnalysis.overall_risk_score)}
          </div>
          <div className="stat-info">
            <span className="stat-label">위험 점수</span>
            <span
              className="severity-badge"
              style={{ backgroundColor: getSeverityColor(riskAnalysis.severity) }}
            >
              {getSeverityLabel(riskAnalysis.severity)}
            </span>
          </div>
        </div>

        <div className="risk-stat-card">
          <div className="stat-number">{riskAnalysis.risk_items.length}</div>
          <div className="stat-label">총 리스크</div>
        </div>

        <div className="risk-stat-card risk-stat-critical">
          <div className="stat-number" style={{ color: '#dc2626' }}>{severityCounts.CRITICAL}</div>
          <div className="stat-label">심각</div>
        </div>

        <div className="risk-stat-card risk-stat-high">
          <div className="stat-number" style={{ color: '#ea580c' }}>{severityCounts.HIGH}</div>
          <div className="stat-label">높음</div>
        </div>

        <div className="risk-stat-card risk-stat-medium">
          <div className="stat-number" style={{ color: '#ca8a04' }}>{severityCounts.MEDIUM}</div>
          <div className="stat-label">중간</div>
        </div>

        <div className="risk-stat-card risk-stat-low">
          <div className="stat-number" style={{ color: '#65a30d' }}>{severityCounts.LOW}</div>
          <div className="stat-label">낮음</div>
        </div>
      </div>

      {/* Risk Summary */}
      <div className="risk-summary-section">
        <h4>분석 요약</h4>
        <div className="risk-summary-content">
          <ReactMarkdown>{riskAnalysis.summary || '요약 정보가 없습니다.'}</ReactMarkdown>
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

      {/* Refresh Analysis Button and Model Selection */}
      <div className="risk-actions">
        <button
          onClick={handleAnalyzeRisk}
          className="refresh-analysis-button"
          disabled={analyzing || analyzingWithModel}
        >
          리스크 재분석
        </button>

        <div className="model-select-row">
          <ModelSelector
            selectedModel={selectedModelId}
            onModelSelect={handleModelSelect}
            token={token}
            disabled={analyzing || analyzingWithModel}
            label="다른 모델로 분석:"
          />
          <button
            className="btn-model-analyze"
            onClick={handleAnalyzeWithModel}
            disabled={!selectedModelId || analyzing || analyzingWithModel}
          >
            {analyzingWithModel ? '분석 중...' : '분석'}
          </button>
        </div>
      </div>

      {modelError && (
        <div className="model-error">
          <span>⚠️ {modelError}</span>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {/* Model Comparison Results */}
      {showComparison && comparisonResults.length > 1 && (
        <div className="risk-comparison-section">
          <div className="comparison-header">
            <h4>모델별 리스크 분석 비교</h4>
            <div className="comparison-controls">
              <span className="result-count">{comparisonResults.length}개 모델 비교 중</span>
              <button className="btn-clear-comparison" onClick={handleClearComparison}>
                비교 초기화
              </button>
            </div>
          </div>

          <div className="comparison-grid">
            {comparisonResults.map((result, index) => {
              const groupedRisks = groupRiskItemsByCategory(result.riskAnalysis.risk_items);
              const severityCounts = countBySeverity(result.riskAnalysis.risk_items);

              return (
                <div key={result.modelId} className={`comparison-card ${result.isLatest ? 'latest' : ''}`}>
                  <div className="comparison-card-header">
                    <div className="model-info">
                      <span className="model-name">{result.modelName}</span>
                      {result.isLatest && <span className="latest-badge">최신</span>}
                    </div>
                    {comparisonResults.length > 1 && (
                      <button
                        className="remove-btn"
                        onClick={() => handleRemoveComparisonResult(result.modelId)}
                      >
                        ×
                      </button>
                    )}
                  </div>

                  <div className="comparison-card-stats">
                    <div className="stat-row">
                      <span className="stat-label">위험 점수:</span>
                      <span className="stat-value score">{result.riskAnalysis.overall_risk_score}점</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">심각도:</span>
                      <span
                        className="severity-badge-small"
                        style={{ backgroundColor: getSeverityColor(result.riskAnalysis.severity) }}
                      >
                        {getSeverityLabel(result.riskAnalysis.severity)}
                      </span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">발견된 리스크:</span>
                      <span className="stat-value">{result.riskAnalysis.risk_items.length}개</span>
                    </div>
                    <div className="stat-row severity-breakdown">
                      <span className="severity-count critical">{severityCounts.CRITICAL}</span>
                      <span className="severity-count high">{severityCounts.HIGH}</span>
                      <span className="severity-count medium">{severityCounts.MEDIUM}</span>
                      <span className="severity-count low">{severityCounts.LOW}</span>
                    </div>
                  </div>

                  <div className="comparison-card-summary">
                    <h5>요약</h5>
                    <div className="summary-content">
                      <ReactMarkdown>{result.riskAnalysis.summary || '요약 없음'}</ReactMarkdown>
                    </div>
                  </div>

                  {result.processingTime && (
                    <div className="processing-time">
                      소요 시간: {(result.processingTime / 1000).toFixed(2)}s
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default RiskAnalysisSection;