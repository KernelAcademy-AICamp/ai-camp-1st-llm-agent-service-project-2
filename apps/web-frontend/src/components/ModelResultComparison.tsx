/**
 * ModelResultComparison - 모델별 결과 비교 컴포넌트
 * 여러 모델의 결과를 나란히 비교할 수 있는 UI
 */

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './ModelResultComparison.css';

// Provider display names
const PROVIDER_NAMES: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
  ollama: 'Ollama',
};

// Provider colors
const PROVIDER_COLORS: Record<string, string> = {
  openai: '#10a37f',
  anthropic: '#cc785c',
  google: '#4285f4',
  ollama: '#333333',
};

export interface ModelResult {
  modelId: string;
  modelName: string;
  provider: string;
  content: string;
  timestamp: string;
  processingTime?: number;
  tokenCount?: number;
  isLatest?: boolean;
}

interface ModelResultComparisonProps {
  results: ModelResult[];
  onRemoveResult?: (modelId: string) => void;
  title?: string;
  showMeta?: boolean;
  renderContent?: (content: string) => React.ReactNode;
}

const ModelResultComparison: React.FC<ModelResultComparisonProps> = ({
  results,
  onRemoveResult,
  title = '모델별 결과 비교',
  showMeta = true,
  renderContent,
}) => {
  const [viewMode, setViewMode] = useState<'side-by-side' | 'stacked'>('side-by-side');
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());

  if (results.length === 0) {
    return null;
  }

  const toggleExpand = (modelId: string) => {
    setExpandedResults(prev => {
      const newSet = new Set(prev);
      if (newSet.has(modelId)) {
        newSet.delete(modelId);
      } else {
        newSet.add(modelId);
      }
      return newSet;
    });
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatProcessingTime = (ms?: number) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  // 단일 결과일 경우 비교 UI 없이 단순 표시
  if (results.length === 1) {
    return null;
  }

  return (
    <div className="model-result-comparison">
      <div className="comparison-header">
        <h4>{title}</h4>
        <div className="comparison-controls">
          <span className="result-count">{results.length}개 모델 비교 중</span>
          <div className="view-mode-toggle">
            <button
              className={`toggle-btn ${viewMode === 'side-by-side' ? 'active' : ''}`}
              onClick={() => setViewMode('side-by-side')}
              title="나란히 보기"
            >
              ⊞
            </button>
            <button
              className={`toggle-btn ${viewMode === 'stacked' ? 'active' : ''}`}
              onClick={() => setViewMode('stacked')}
              title="세로로 보기"
            >
              ☰
            </button>
          </div>
        </div>
      </div>

      <div className={`comparison-results ${viewMode}`}>
        {results.map((result, index) => (
          <div
            key={result.modelId}
            className={`result-card ${result.isLatest ? 'latest' : ''} ${
              expandedResults.has(result.modelId) ? 'expanded' : ''
            }`}
          >
            <div className="result-card-header">
              <div className="model-info">
                <span
                  className="provider-dot"
                  style={{ backgroundColor: PROVIDER_COLORS[result.provider] || '#666' }}
                />
                <span className="model-name">{result.modelName}</span>
                <span className="provider-name">
                  {PROVIDER_NAMES[result.provider] || result.provider}
                </span>
                {result.isLatest && <span className="latest-badge">최신</span>}
              </div>
              <div className="result-actions">
                {onRemoveResult && results.length > 1 && (
                  <button
                    className="remove-btn"
                    onClick={() => onRemoveResult(result.modelId)}
                    title="결과 제거"
                  >
                    ×
                  </button>
                )}
              </div>
            </div>

            {showMeta && (
              <div className="result-meta">
                <span className="meta-item">
                  <span className="meta-label">생성:</span>
                  <span className="meta-value">{formatTime(result.timestamp)}</span>
                </span>
                {result.processingTime && (
                  <span className="meta-item">
                    <span className="meta-label">소요:</span>
                    <span className="meta-value">{formatProcessingTime(result.processingTime)}</span>
                  </span>
                )}
                {result.tokenCount && (
                  <span className="meta-item">
                    <span className="meta-label">토큰:</span>
                    <span className="meta-value">{result.tokenCount.toLocaleString()}</span>
                  </span>
                )}
              </div>
            )}

            <div className="result-content">
              {renderContent ? (
                renderContent(result.content)
              ) : (
                <ReactMarkdown>{result.content}</ReactMarkdown>
              )}
            </div>

            {result.content.length > 500 && (
              <button
                className="expand-toggle"
                onClick={() => toggleExpand(result.modelId)}
              >
                {expandedResults.has(result.modelId) ? '접기 ▲' : '더 보기 ▼'}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ModelResultComparison;
