import React, { useState, useMemo } from 'react';
import { Summary } from '../types';
import { apiClient } from '../api/client';
import ModelSelector from './ModelSelector';
import ModelResultComparison, { ModelResult } from './ModelResultComparison';
import { applyPartialMasking } from '../utils/piiMasker';
import './SummarySection.css';

interface SummarySectionProps {
  summary: Summary | null;
  loading: boolean;
  error: string | null;
  onGenerate: () => void;
  generating: boolean;
  // New props for model selection
  documentId?: string;
  token?: string;
}

const SummarySection: React.FC<SummarySectionProps> = ({
  summary,
  loading,
  error,
  onGenerate,
  generating,
  documentId,
  token,
}) => {
  // Model selection state
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [selectedModelName, setSelectedModelName] = useState<string>('');
  const [generatingWithModel, setGeneratingWithModel] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);

  // Comparison results - store multiple model results (only when user explicitly generates with different model)
  const [comparisonResults, setComparisonResults] = useState<ModelResult[]>([]);

  // PII 마스킹된 요약 내용
  const maskedSummaryContent = useMemo(() => {
    return summary?.content ? applyPartialMasking(summary.content) : '';
  }, [summary?.content]);

  // PII 마스킹된 비교 결과
  const maskedComparisonResults = useMemo(() => {
    return comparisonResults.map((result) => ({
      ...result,
      content: applyPartialMasking(result.content),
    }));
  }, [comparisonResults]);

  // Helper to guess provider from model name
  const getProviderFromModel = (modelName: string): string => {
    const name = modelName.toLowerCase();
    if (name.includes('gpt') || name.includes('openai')) return 'openai';
    if (name.includes('claude') || name.includes('anthropic')) return 'anthropic';
    if (name.includes('gemini') || name.includes('google')) return 'google';
    if (name.includes('ollama') || name.includes('local')) return 'ollama';
    return 'openai'; // default
  };

  const handleModelSelect = (modelId: string, modelName: string) => {
    setSelectedModelId(modelId);
    setSelectedModelName(modelName);
    setModelError(null);
  };

  const handleGenerateWithModel = async () => {
    if (!documentId || !selectedModelId || !summary) return;

    setGeneratingWithModel(true);
    setModelError(null);

    try {
      const response = await apiClient.generateSummaryWithModel(
        documentId,
        selectedModelId,
        token
      );

      if (response.success && response.summary) {
        const newResult: ModelResult = {
          modelId: selectedModelId,
          modelName: response.model_used || selectedModelName,
          provider: getProviderFromModel(response.model_used || selectedModelName),
          content: response.summary.content,
          timestamp: response.summary.created_at,
          processingTime: response.processing_time_ms,
          isLatest: true,
        };

        setComparisonResults(prev => {
          // If comparison results are empty, add the current summary first for comparison
          if (prev.length === 0 && summary) {
            const currentSummaryResult: ModelResult = {
              modelId: summary.llm_model,
              modelName: summary.llm_model,
              provider: getProviderFromModel(summary.llm_model),
              content: summary.content,
              timestamp: summary.created_at,
              isLatest: false,
            };
            return [currentSummaryResult, newResult];
          }
          // Mark all previous results as not latest and add new one
          return [
            ...prev.map(r => ({ ...r, isLatest: false })),
            newResult,
          ];
        });
      }
    } catch (err: any) {
      console.error('Failed to generate summary with model:', err);
      setModelError(err.message || '요약 생성에 실패했습니다.');
    } finally {
      setGeneratingWithModel(false);
    }
  };

  const handleRemoveResult = (modelId: string) => {
    setComparisonResults(prev => prev.filter(r => r.modelId !== modelId));
  };

  const handleClearComparison = () => {
    // Clear all comparison results - user can start fresh comparison later
    setComparisonResults([]);
  };

  return (
    <div className="summary-section">
      <div className="section-header">
        <h2>문서 요약</h2>
        <div className="header-actions">
          {!summary && !loading && (
            <button
              className="btn-primary"
              onClick={onGenerate}
              disabled={generating}
            >
              {generating ? '요약 생성 중...' : '요약 생성'}
            </button>
          )}
        </div>
      </div>

      {loading && (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>요약을 불러오는 중...</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <p>{error}</p>
        </div>
      )}

      {summary && !loading && (
        <div className="summary-content">
          <div className="summary-meta">
            <span className="meta-item">
              <strong>모델:</strong> {summary.llm_model}
            </span>
            <span className="meta-item">
              <strong>유형:</strong> {summary.summary_type}
            </span>
            <span className="meta-item">
              <strong>생성 일시:</strong>{' '}
              {new Date(summary.created_at).toLocaleString('ko-KR')}
            </span>
          </div>

          <div className="summary-text">
            <p>{maskedSummaryContent}</p>
          </div>

          {summary.meta && Object.keys(summary.meta).length > 0 && (
            <div className="summary-metadata">
              <details>
                <summary>추가 정보</summary>
                <pre>{JSON.stringify(summary.meta, null, 2)}</pre>
              </details>
            </div>
          )}

          {/* Model Selection and Re-generate */}
          <div className="model-regenerate-section">
            <div className="regenerate-row">
              <button
                className="btn-secondary"
                onClick={onGenerate}
                disabled={generating || generatingWithModel}
              >
                {generating ? '재생성 중...' : '요약 재생성'}
              </button>

              {documentId && (
                <div className="model-select-row">
                  <ModelSelector
                    selectedModel={selectedModelId}
                    onModelSelect={handleModelSelect}
                    token={token}
                    disabled={generating || generatingWithModel}
                    label="다른 모델로 생성:"
                  />
                  <button
                    className="btn-model-generate"
                    onClick={handleGenerateWithModel}
                    disabled={!selectedModelId || generating || generatingWithModel}
                  >
                    {generatingWithModel ? '생성 중...' : '생성'}
                  </button>
                </div>
              )}
            </div>

            {modelError && (
              <div className="model-error">
                <span>⚠️ {modelError}</span>
              </div>
            )}
          </div>

          {/* Comparison Results (PII 마스킹 적용) */}
          {maskedComparisonResults.length > 1 && (
            <div className="comparison-section">
              <div className="comparison-actions">
                <button
                  className="btn-clear-comparison"
                  onClick={handleClearComparison}
                >
                  비교 초기화
                </button>
              </div>
              <ModelResultComparison
                results={maskedComparisonResults}
                onRemoveResult={handleRemoveResult}
                title="모델별 요약 결과 비교"
              />
            </div>
          )}
        </div>
      )}

      {!summary && !loading && !error && !generating && (
        <div className="empty-state">
          <p>아직 생성된 요약이 없습니다.</p>
          <p className="small">
            "요약 생성" 버튼을 클릭하여 문서의 핵심 내용을 요약해보세요.
          </p>
        </div>
      )}
    </div>
  );
};

export default SummarySection;
