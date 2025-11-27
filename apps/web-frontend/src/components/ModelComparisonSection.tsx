/**
 * ModelComparisonSection - 문서 상세 페이지에 통합된 LLM 모델 비교 섹션
 * 문서의 텍스트를 자동으로 사용하여 여러 모델의 응답을 비교합니다.
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import {
  LLMModelConfigListItem,
  CompareTaskType,
  CompareResponse,
  ModelComparisonResult,
} from '../types';
import './ModelComparisonSection.css';

interface ModelComparisonSectionProps {
  documentId: string;
  documentTitle: string;
  documentText?: string;
  token?: string;
}

// Task type options for document analysis
const TASK_TYPES: { value: CompareTaskType; label: string; description: string }[] = [
  { value: 'summarize', label: '문서 요약', description: '문서 내용을 요약합니다' },
  { value: 'clauses', label: '조항 추출', description: '핵심 조항을 추출합니다' },
  { value: 'risk_analysis', label: '리스크 분석', description: '잠재적 위험 요소를 분석합니다' },
  { value: 'case_analysis', label: '사건 분석', description: '법적 쟁점을 분석합니다' },
  { value: 'chat', label: '일반 질의', description: '문서에 대해 질문합니다' },
];

// Provider display names
const PROVIDER_NAMES: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
  ollama: 'Ollama (Local)',
};

const ModelComparisonSection: React.FC<ModelComparisonSectionProps> = ({
  documentId,
  documentTitle,
  documentText,
  token,
}) => {
  // State
  const [models, setModels] = useState<LLMModelConfigListItem[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [taskType, setTaskType] = useState<CompareTaskType>('summarize');
  const [customQuestion, setCustomQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonResult, setComparisonResult] = useState<CompareResponse | null>(null);

  // Load available models on mount
  useEffect(() => {
    if (models.length === 0) {
      loadModels();
    }
  }, []);

  const loadModels = async () => {
    setIsLoadingModels(true);
    try {
      const response = await apiClient.getActiveLLMModels(token);
      setModels(response);
      // Select first 2 models by default for quick comparison
      if (response.length >= 2) {
        setSelectedModels([response[0].id, response[1].id]);
      } else if (response.length === 1) {
        setSelectedModels([response[0].id]);
      }
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
    if (selectedModels.length < 2) {
      setError('2개 이상의 모델을 선택해주세요.');
      return;
    }

    // Build the text to compare based on task type
    let textToCompare = '';

    if (taskType === 'chat' && customQuestion.trim()) {
      // For chat, use custom question with document context
      textToCompare = `다음 문서에 대한 질문입니다:\n\n문서 제목: ${documentTitle}\n\n질문: ${customQuestion}`;
      if (documentText) {
        textToCompare += `\n\n문서 내용:\n${documentText.substring(0, 8000)}`;
      }
    } else if (documentText) {
      // Use document text for analysis
      textToCompare = `문서 제목: ${documentTitle}\n\n${documentText.substring(0, 10000)}`;
    } else {
      setError('문서 텍스트가 없습니다. 문서가 처리 완료되었는지 확인해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setComparisonResult(null);

    try {
      const response = await apiClient.compareLLMModels(
        {
          text: textToCompare,
          task_type: taskType,
          model_ids: selectedModels,
        },
        token
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
      <span className="mcs-status-badge success">성공</span>
    ) : (
      <span className="mcs-status-badge error">실패</span>
    );
  };

  const getBestBadge = (result: ModelComparisonResult) => {
    if (!comparisonResult) return null;

    const badges = [];
    if (comparisonResult.fastest_model === result.model_name) {
      badges.push(<span key="fastest" className="mcs-best-badge fastest">🚀 최고 속도</span>);
    }
    if (comparisonResult.cheapest_model === result.model_name) {
      badges.push(<span key="cheapest" className="mcs-best-badge cheapest">💰 최저 비용</span>);
    }
    return badges;
  };

  return (
    <div className="model-comparison-section">
      <div className="mcs-header">
        <h3>LLM 모델 비교</h3>
      </div>

      <div className="mcs-content">
          {error && (
            <div className="mcs-error">
              <span>⚠️ {error}</span>
              <button onClick={() => setError(null)}>×</button>
            </div>
          )}

          {/* Model Selection */}
          <div className="mcs-model-selection">
            <h4>비교할 모델 선택</h4>
            {isLoadingModels ? (
              <div className="mcs-loading">모델 로딩 중...</div>
            ) : models.length === 0 ? (
              <div className="mcs-empty">활성화된 모델이 없습니다.</div>
            ) : (
              <>
                <div className="mcs-select-all">
                  <label>
                    <input
                      type="checkbox"
                      checked={selectedModels.length === models.length}
                      onChange={handleSelectAll}
                    />
                    전체 선택 ({selectedModels.length}/{models.length})
                  </label>
                </div>
                <div className="mcs-model-grid">
                  {models.map(model => (
                    <label key={model.id} className={`mcs-model-item ${selectedModels.includes(model.id) ? 'selected' : ''}`}>
                      <input
                        type="checkbox"
                        checked={selectedModels.includes(model.id)}
                        onChange={() => handleModelToggle(model.id)}
                      />
                      <div className="mcs-model-info">
                        <span className="mcs-model-name">{model.name}</span>
                        <span className="mcs-model-provider">
                          {PROVIDER_NAMES[model.provider] || model.provider}
                        </span>
                        {model.is_default && (
                          <span className="mcs-default-badge">기본</span>
                        )}
                      </div>
                    </label>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Task Type Selection */}
          <div className="mcs-task-selection">
            <h4>분석 유형</h4>
            <div className="mcs-task-grid">
              {TASK_TYPES.map(type => (
                <button
                  key={type.value}
                  className={`mcs-task-btn ${taskType === type.value ? 'active' : ''}`}
                  onClick={() => setTaskType(type.value)}
                >
                  <span className="mcs-task-label">{type.label}</span>
                  <span className="mcs-task-desc">{type.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Custom Question for chat type */}
          {taskType === 'chat' && (
            <div className="mcs-custom-question">
              <h4>질문 입력</h4>
              <textarea
                value={customQuestion}
                onChange={(e) => setCustomQuestion(e.target.value)}
                placeholder="문서에 대해 질문하세요..."
                rows={3}
              />
            </div>
          )}

          {/* Compare Button */}
          <button
            className="mcs-compare-btn"
            onClick={handleCompare}
            disabled={isLoading || selectedModels.length < 2 || (taskType === 'chat' && !customQuestion.trim())}
          >
            {isLoading ? '비교 중...' : `${selectedModels.length}개 모델 비교 시작`}
          </button>

          {/* Results */}
          {isLoading && (
            <div className="mcs-loading-state">
              <div className="mcs-spinner"></div>
              <p>모델 응답 비교 중...</p>
              <small>선택한 모델 수에 따라 시간이 소요될 수 있습니다.</small>
            </div>
          )}

          {comparisonResult && !isLoading && (
            <div className="mcs-results">
              {/* Summary */}
              <div className="mcs-summary">
                <h4>비교 결과 요약</h4>
                <div className="mcs-summary-grid">
                  <div className="mcs-summary-item">
                    <span className="label">총 모델</span>
                    <span className="value">{comparisonResult.total_models}개</span>
                  </div>
                  <div className="mcs-summary-item">
                    <span className="label">성공</span>
                    <span className="value success">
                      {comparisonResult.results.filter(r => r.status === 'success').length}개
                    </span>
                  </div>
                  <div className="mcs-summary-item">
                    <span className="label">총 비용</span>
                    <span className="value">
                      {formatCost(comparisonResult.summary?.total_cost || 0)}
                    </span>
                  </div>
                  <div className="mcs-summary-item">
                    <span className="label">평균 지연</span>
                    <span className="value">
                      {formatLatency(comparisonResult.summary?.avg_latency_ms || 0)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Results Table */}
              <div className="mcs-table-container">
                <h4>상세 비교 결과</h4>
                <table className="mcs-table">
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
                          <div className="mcs-model-cell">
                            <strong>{result.model_name}</strong>
                            <small>{PROVIDER_NAMES[result.provider] || result.provider}</small>
                            <div className="badges">{getBestBadge(result)}</div>
                          </div>
                        </td>
                        <td>{getStatusBadge(result.status)}</td>
                        <td>{formatLatency(result.latency_ms)}</td>
                        <td>
                          {result.total_tokens.toLocaleString()}
                          <small>({result.prompt_tokens} + {result.response_tokens})</small>
                        </td>
                        <td>{formatCost(result.estimated_cost)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Response Cards */}
              <div className="mcs-responses">
                <h4>응답 내용 비교</h4>
                <div className="mcs-responses-grid">
                  {comparisonResult.results
                    .filter(r => r.status === 'success')
                    .map((result, idx) => (
                      <div key={idx} className="mcs-response-card">
                        <div className="mcs-response-header">
                          <strong>{result.model_name}</strong>
                          {getBestBadge(result)}
                        </div>
                        <div className="mcs-response-content">
                          {result.response_text || '(응답 없음)'}
                        </div>
                        <div className="mcs-response-footer">
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
                <div className="mcs-errors">
                  <h4>오류 메시지</h4>
                  {comparisonResult.results
                    .filter(r => r.status === 'error')
                    .map((result, idx) => (
                      <div key={idx} className="mcs-error-item">
                        <strong>{result.model_name}:</strong>
                        <span>{result.error_message || '알 수 없는 오류'}</span>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}
      </div>
    </div>
  );
};

export default ModelComparisonSection;
