/**
 * LLM Model Comparison Page
 * 여러 LLM 모델의 응답을 비교하는 페이지
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { apiClient } from '../../api/client';
import {
  LLMModelConfigListItem,
  CompareTaskType,
  CompareResponse,
  ModelComparisonResult,
} from '../../types';
import './ModelComparison.css';

// Task type options
const TASK_TYPES: { value: CompareTaskType; label: string }[] = [
  { value: 'summarize', label: '문서 요약' },
  { value: 'clauses', label: '조항 추출' },
  { value: 'risk_analysis', label: '리스크 분석' },
  { value: 'case_analysis', label: '사건 분석' },
  { value: 'chat', label: '일반 질의' },
  { value: 'other', label: '기타' },
];

// Provider display names
const PROVIDER_NAMES: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
  ollama: 'Ollama (Local)',
};

const ModelComparison: React.FC = () => {
  const { token } = useAuth();

  // State
  const [models, setModels] = useState<LLMModelConfigListItem[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [inputText, setInputText] = useState('');
  const [taskType, setTaskType] = useState<CompareTaskType>('summarize');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingModels, setIsLoadingModels] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [comparisonResult, setComparisonResult] = useState<CompareResponse | null>(null);

  // Load available models on mount
  useEffect(() => {
    loadModels();
  }, [token]);

  const loadModels = async () => {
    setIsLoadingModels(true);
    try {
      const response = await apiClient.getActiveLLMModels(token || undefined);
      setModels(response);
      // Select all models by default
      setSelectedModels(response.map(m => m.id));
    } catch (err: any) {
      console.error('Failed to load models:', err);
      setError('모델 목록을 불러오는데 실패했습니다.');
    } finally {
      setIsLoadingModels(false);
    }
  };

  const handleModelToggle = (modelId: string) => {
    setSelectedModels(prev => {
      if (prev.includes(modelId)) {
        return prev.filter(id => id !== modelId);
      } else {
        return [...prev, modelId];
      }
    });
  };

  const handleSelectAll = () => {
    if (selectedModels.length === models.length) {
      setSelectedModels([]);
    } else {
      setSelectedModels(models.map(m => m.id));
    }
  };

  const handleCompare = async () => {
    if (!inputText.trim()) {
      setError('비교할 텍스트를 입력해주세요.');
      return;
    }

    if (selectedModels.length < 2) {
      setError('2개 이상의 모델을 선택해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setComparisonResult(null);

    try {
      const response = await apiClient.compareLLMModels(
        {
          text: inputText,
          task_type: taskType,
          model_ids: selectedModels,
        },
        token || undefined
      );
      setComparisonResult(response);
    } catch (err: any) {
      console.error('Comparison failed:', err);
      setError(err.message || '비교에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCost = (cost: number): string => {
    if (cost === 0) return '$0.000000';
    return `$${cost.toFixed(6)}`;
  };

  const formatLatency = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const getStatusBadge = (status: string) => {
    return status === 'success' ? (
      <span className="status-badge success">성공</span>
    ) : (
      <span className="status-badge error">실패</span>
    );
  };

  const getBestBadge = (result: ModelComparisonResult) => {
    if (!comparisonResult) return null;

    const badges = [];
    if (comparisonResult.fastest_model === result.model_name) {
      badges.push(<span key="fastest" className="best-badge fastest">🚀 최고 속도</span>);
    }
    if (comparisonResult.cheapest_model === result.model_name) {
      badges.push(<span key="cheapest" className="best-badge cheapest">💰 최저 비용</span>);
    }
    return badges;
  };

  return (
    <div className="model-comparison-page">
      <header className="page-header">
        <h1>LLM 모델 비교</h1>
        <p>여러 LLM 모델의 응답을 비교하고 최적의 모델을 선택하세요</p>
      </header>

      {error && (
        <div className="error-message">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="comparison-container">
        {/* Left Panel - Input */}
        <div className="input-panel">
          <div className="panel-section">
            <h3>모델 선택</h3>
            {isLoadingModels ? (
              <div className="loading-spinner">모델 로딩 중...</div>
            ) : models.length === 0 ? (
              <div className="empty-state">활성화된 모델이 없습니다.</div>
            ) : (
              <>
                <div className="select-all-row">
                  <label>
                    <input
                      type="checkbox"
                      checked={selectedModels.length === models.length}
                      onChange={handleSelectAll}
                    />
                    전체 선택 ({selectedModels.length}/{models.length})
                  </label>
                </div>
                <div className="model-list">
                  {models.map(model => (
                    <label key={model.id} className="model-item">
                      <input
                        type="checkbox"
                        checked={selectedModels.includes(model.id)}
                        onChange={() => handleModelToggle(model.id)}
                      />
                      <div className="model-info">
                        <span className="model-name">{model.name}</span>
                        <span className="model-provider">
                          {PROVIDER_NAMES[model.provider] || model.provider}
                        </span>
                        {model.is_default && (
                          <span className="default-badge">기본</span>
                        )}
                      </div>
                      <div className="model-cost">
                        <small>
                          입력: ${parseFloat(model.input_cost_per_1k).toFixed(4)}/1K
                        </small>
                        <small>
                          출력: ${parseFloat(model.output_cost_per_1k).toFixed(4)}/1K
                        </small>
                      </div>
                    </label>
                  ))}
                </div>
              </>
            )}
          </div>

          <div className="panel-section">
            <h3>작업 유형</h3>
            <select
              value={taskType}
              onChange={(e) => setTaskType(e.target.value as CompareTaskType)}
              className="task-select"
            >
              {TASK_TYPES.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div className="panel-section">
            <h3>입력 텍스트</h3>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="비교할 문서 내용이나 질문을 입력하세요..."
              className="input-textarea"
              rows={10}
            />
            <div className="char-count">
              {inputText.length} 자 ({Math.ceil(inputText.length / 4)} 예상 토큰)
            </div>
          </div>

          <button
            className="compare-button"
            onClick={handleCompare}
            disabled={isLoading || selectedModels.length < 2 || !inputText.trim()}
          >
            {isLoading ? '비교 중...' : `${selectedModels.length}개 모델 비교`}
          </button>
        </div>

        {/* Right Panel - Results */}
        <div className="results-panel">
          {isLoading ? (
            <div className="loading-state">
              <div className="loading-spinner large" />
              <p>모델 응답 비교 중...</p>
              <small>선택한 모델 수에 따라 시간이 소요될 수 있습니다.</small>
            </div>
          ) : comparisonResult ? (
            <>
              {/* Summary */}
              <div className="results-summary">
                <h3>비교 결과 요약</h3>
                <div className="summary-grid">
                  <div className="summary-item">
                    <span className="label">총 모델 수</span>
                    <span className="value">{comparisonResult.total_models}개</span>
                  </div>
                  <div className="summary-item">
                    <span className="label">성공</span>
                    <span className="value success">
                      {comparisonResult.results.filter(r => r.status === 'success').length}개
                    </span>
                  </div>
                  <div className="summary-item">
                    <span className="label">실패</span>
                    <span className="value error">
                      {comparisonResult.results.filter(r => r.status === 'error').length}개
                    </span>
                  </div>
                  <div className="summary-item">
                    <span className="label">총 토큰</span>
                    <span className="value">
                      {comparisonResult.summary?.total_tokens?.toLocaleString() || 0}
                    </span>
                  </div>
                  <div className="summary-item">
                    <span className="label">총 비용</span>
                    <span className="value">
                      {formatCost(comparisonResult.summary?.total_cost || 0)}
                    </span>
                  </div>
                  <div className="summary-item">
                    <span className="label">평균 지연</span>
                    <span className="value">
                      {formatLatency(comparisonResult.summary?.avg_latency_ms || 0)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Results Table */}
              <div className="results-table-container">
                <h3>상세 비교 결과</h3>
                <table className="results-table">
                  <thead>
                    <tr>
                      <th>모델</th>
                      <th>상태</th>
                      <th>지연시간</th>
                      <th>토큰</th>
                      <th>비용</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisonResult.results.map((result, idx) => (
                      <tr key={idx} className={result.status === 'error' ? 'error-row' : ''}>
                        <td>
                          <div className="model-cell">
                            <strong>{result.model_name}</strong>
                            <small>{PROVIDER_NAMES[result.provider] || result.provider}</small>
                            <div className="badges">
                              {getBestBadge(result)}
                            </div>
                          </div>
                        </td>
                        <td>{getStatusBadge(result.status)}</td>
                        <td>{formatLatency(result.latency_ms)}</td>
                        <td>
                          {result.total_tokens.toLocaleString()}
                          <small>
                            ({result.prompt_tokens} + {result.response_tokens})
                          </small>
                        </td>
                        <td>{formatCost(result.estimated_cost)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Response Comparison */}
              <div className="responses-comparison">
                <h3>응답 내용 비교</h3>
                <div className="responses-grid">
                  {comparisonResult.results
                    .filter(r => r.status === 'success')
                    .map((result, idx) => (
                      <div key={idx} className="response-card">
                        <div className="response-header">
                          <strong>{result.model_name}</strong>
                          {getBestBadge(result)}
                        </div>
                        <div className="response-content">
                          {result.response_text || '(응답 없음)'}
                        </div>
                        <div className="response-footer">
                          <span>{formatLatency(result.latency_ms)}</span>
                          <span>{result.total_tokens.toLocaleString()} tokens</span>
                          <span>{formatCost(result.estimated_cost)}</span>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Error Messages */}
              {comparisonResult.results.some(r => r.status === 'error') && (
                <div className="error-messages">
                  <h3>오류 메시지</h3>
                  {comparisonResult.results
                    .filter(r => r.status === 'error')
                    .map((result, idx) => (
                      <div key={idx} className="error-item">
                        <strong>{result.model_name}:</strong>
                        <span>{result.error_message || '알 수 없는 오류'}</span>
                      </div>
                    ))}
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <h3>비교 결과가 없습니다</h3>
              <p>왼쪽에서 모델을 선택하고 텍스트를 입력한 후 비교를 시작하세요.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ModelComparison;
