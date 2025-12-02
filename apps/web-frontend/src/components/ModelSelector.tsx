/**
 * ModelSelector - 모델 선택 드롭다운 컴포넌트
 * 각 분석 섹션에서 LLM 모델을 선택할 수 있게 해주는 공통 컴포넌트
 */

import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '../api/client';
import { LLMModelConfigListItem } from '../types';
import './ModelSelector.css';

// Provider display names
const PROVIDER_NAMES: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
  ollama: 'Ollama',
};

// Provider icons/colors
const PROVIDER_COLORS: Record<string, string> = {
  openai: '#10a37f',
  anthropic: '#cc785c',
  google: '#4285f4',
  ollama: '#333333',
};

interface ModelSelectorProps {
  selectedModel: string | null;
  onModelSelect: (modelId: string, modelName: string) => void;
  token?: string;
  disabled?: boolean;
  label?: string;
  showProviderBadge?: boolean;
}

const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModel,
  onModelSelect,
  token,
  disabled = false,
  label = '모델 선택',
  showProviderBadge = true,
}) => {
  const [models, setModels] = useState<LLMModelConfigListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadModels();
  }, [token]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadModels = async () => {
    setLoading(true);
    try {
      const response = await apiClient.getActiveLLMModels(token);
      setModels(response);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load models:', err);
      setError('모델 목록을 불러오지 못했습니다');
    } finally {
      setLoading(false);
    }
  };

  const getSelectedModelInfo = (): LLMModelConfigListItem | undefined => {
    return models.find(m => m.id === selectedModel);
  };

  const selectedModelInfo = getSelectedModelInfo();

  const handleModelClick = (model: LLMModelConfigListItem) => {
    onModelSelect(model.id, model.name);
    setIsOpen(false);
  };

  if (loading) {
    return (
      <div className="model-selector loading">
        <span className="model-selector-label">{label}</span>
        <div className="model-selector-button disabled">
          <span className="loading-text">로딩 중...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="model-selector error">
        <span className="model-selector-label">{label}</span>
        <div className="model-selector-button error" onClick={loadModels}>
          <span className="error-text">{error}</span>
          <span className="retry-icon">↻</span>
        </div>
      </div>
    );
  }

  return (
    <div className="model-selector" ref={dropdownRef}>
      <span className="model-selector-label">{label}</span>
      <div
        className={`model-selector-button ${disabled ? 'disabled' : ''} ${isOpen ? 'open' : ''}`}
        onClick={() => !disabled && setIsOpen(!isOpen)}
      >
        {selectedModelInfo ? (
          <>
            {showProviderBadge && (
              <span
                className="provider-dot"
                style={{ backgroundColor: PROVIDER_COLORS[selectedModelInfo.provider] || '#666' }}
              />
            )}
            <span className="selected-model-name">{selectedModelInfo.name}</span>
            {showProviderBadge && (
              <span className="provider-badge">
                {PROVIDER_NAMES[selectedModelInfo.provider] || selectedModelInfo.provider}
              </span>
            )}
          </>
        ) : (
          <span className="placeholder">모델을 선택하세요</span>
        )}
        <span className={`dropdown-arrow ${isOpen ? 'open' : ''}`}>▾</span>
      </div>

      {isOpen && (
        <div className="model-selector-dropdown">
          {models.length === 0 ? (
            <div className="dropdown-empty">활성화된 모델이 없습니다</div>
          ) : (
            models.map(model => (
              <div
                key={model.id}
                className={`dropdown-item ${model.id === selectedModel ? 'selected' : ''}`}
                onClick={() => handleModelClick(model)}
              >
                <span
                  className="provider-dot"
                  style={{ backgroundColor: PROVIDER_COLORS[model.provider] || '#666' }}
                />
                <div className="model-info">
                  <span className="model-name">{model.name}</span>
                  <span className="model-provider">
                    {PROVIDER_NAMES[model.provider] || model.provider}
                  </span>
                </div>
                {model.is_default && <span className="default-badge">기본</span>}
                {model.id === selectedModel && <span className="check-icon">✓</span>}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default ModelSelector;
