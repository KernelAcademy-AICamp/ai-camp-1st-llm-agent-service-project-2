/**
 * DocumentFilter Component (Session 13-C)
 *
 * RAG 검색 필터 패널 컴포넌트
 * - 문서 타입 필터 (계약서, 사건, 법령, 기타)
 * - 업로드 날짜 범위 필터
 * - 문서 상태 필터 (업로드됨, 전처리됨, 임베딩됨)
 * - 키워드 검색 (문서 제목만 검색)
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  RAGFilterOptions,
  UserDocumentType,
  UserDocumentStatus,
} from '../../types';
import './DocumentFilter.css';

interface DocumentFilterProps {
  filters: RAGFilterOptions;
  onFilterChange: (filters: RAGFilterOptions) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

// Document type options
const DOC_TYPE_OPTIONS: { value: UserDocumentType; label: string }[] = [
  { value: 'CONTRACT', label: '계약서' },
  { value: 'CASE', label: '사건' },
  { value: 'STATUTE', label: '법령' },
  { value: 'PRECEDENT', label: '판례' },
  { value: 'OTHER', label: '기타' },
];

// Document status options
const STATUS_OPTIONS: { value: UserDocumentStatus; label: string }[] = [
  { value: 'UPLOADED', label: '업로드됨' },
  { value: 'PREPROCESSED', label: '전처리됨' },
  { value: 'EMBEDDED', label: '임베딩됨' },
];

const DocumentFilter: React.FC<DocumentFilterProps> = ({
  filters,
  onFilterChange,
  isCollapsed = false,
  onToggleCollapse,
}) => {
  // Local state for keyword input (debounced)
  const [keywordInput, setKeywordInput] = useState(filters.keyword || '');

  // Sync keyword input with filters
  useEffect(() => {
    setKeywordInput(filters.keyword || '');
  }, [filters.keyword]);

  // Debounced keyword update
  useEffect(() => {
    const timer = setTimeout(() => {
      if (keywordInput !== filters.keyword) {
        onFilterChange({
          ...filters,
          keyword: keywordInput || undefined,
        });
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [keywordInput, filters, onFilterChange]);

  // Handle document type checkbox change
  const handleDocTypeChange = useCallback(
    (docType: UserDocumentType, checked: boolean) => {
      const currentTypes = filters.doc_types || [];
      let newTypes: UserDocumentType[];

      if (checked) {
        newTypes = [...currentTypes, docType];
      } else {
        newTypes = currentTypes.filter((t) => t !== docType);
      }

      onFilterChange({
        ...filters,
        doc_types: newTypes.length > 0 ? newTypes : undefined,
      });
    },
    [filters, onFilterChange]
  );

  // Handle status checkbox change
  const handleStatusChange = useCallback(
    (status: UserDocumentStatus, checked: boolean) => {
      const currentStatuses = filters.statuses || [];
      let newStatuses: UserDocumentStatus[];

      if (checked) {
        newStatuses = [...currentStatuses, status];
      } else {
        newStatuses = currentStatuses.filter((s) => s !== status);
      }

      onFilterChange({
        ...filters,
        statuses: newStatuses.length > 0 ? newStatuses : undefined,
      });
    },
    [filters, onFilterChange]
  );

  // Handle date change
  const handleDateChange = useCallback(
    (field: 'date_from' | 'date_to', value: string) => {
      onFilterChange({
        ...filters,
        [field]: value || undefined,
      });
    },
    [filters, onFilterChange]
  );

  // Clear all filters
  const handleClearAll = useCallback(() => {
    setKeywordInput('');
    onFilterChange({
      statuses: ['EMBEDDED'], // Keep default status
    });
  }, [onFilterChange]);

  // Check if any filters are active (excluding default status)
  const hasActiveFilters =
    (filters.doc_types && filters.doc_types.length > 0) ||
    (filters.statuses &&
      !(filters.statuses.length === 1 && filters.statuses[0] === 'EMBEDDED')) ||
    filters.date_from ||
    filters.date_to ||
    filters.keyword;

  if (isCollapsed) {
    return (
      <div className="document-filter document-filter--collapsed">
        <button
          className="document-filter__toggle"
          onClick={onToggleCollapse}
          title="필터 패널 열기"
        >
          <span className="document-filter__toggle-icon">☰</span>
          <span className="document-filter__toggle-label">필터</span>
          {hasActiveFilters && (
            <span className="document-filter__badge">!</span>
          )}
        </button>
      </div>
    );
  }

  return (
    <div className="document-filter">
      {/* Header */}
      <div className="document-filter__header">
        <h3 className="document-filter__title">검색 필터</h3>
        <div className="document-filter__actions">
          {hasActiveFilters && (
            <button
              className="document-filter__clear-btn"
              onClick={handleClearAll}
              title="필터 초기화"
            >
              초기화
            </button>
          )}
          {onToggleCollapse && (
            <button
              className="document-filter__collapse-btn"
              onClick={onToggleCollapse}
              title="필터 패널 접기"
            >
              ◀
            </button>
          )}
        </div>
      </div>

      {/* Keyword Search */}
      <div className="document-filter__section">
        <label className="document-filter__label">키워드 검색</label>
        <input
          type="text"
          className="document-filter__input"
          placeholder="문서 제목 검색..."
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
        />
        <span className="document-filter__hint">문서 제목에서만 검색됩니다</span>
      </div>

      {/* Document Type Filter */}
      <div className="document-filter__section">
        <label className="document-filter__label">문서 타입</label>
        <div className="document-filter__checkbox-group">
          {DOC_TYPE_OPTIONS.map((option) => (
            <label key={option.value} className="document-filter__checkbox">
              <input
                type="checkbox"
                checked={filters.doc_types?.includes(option.value) || false}
                onChange={(e) =>
                  handleDocTypeChange(option.value, e.target.checked)
                }
              />
              <span className="document-filter__checkbox-label">
                {option.label}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Document Status Filter */}
      <div className="document-filter__section">
        <label className="document-filter__label">문서 상태</label>
        <div className="document-filter__checkbox-group">
          {STATUS_OPTIONS.map((option) => (
            <label key={option.value} className="document-filter__checkbox">
              <input
                type="checkbox"
                checked={filters.statuses?.includes(option.value) || false}
                onChange={(e) =>
                  handleStatusChange(option.value, e.target.checked)
                }
              />
              <span className="document-filter__checkbox-label">
                {option.label}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Date Range Filter */}
      <div className="document-filter__section">
        <label className="document-filter__label">업로드 날짜</label>
        <div className="document-filter__date-range">
          <div className="document-filter__date-field">
            <label className="document-filter__date-label">시작일</label>
            <input
              type="date"
              className="document-filter__date-input"
              value={filters.date_from || ''}
              onChange={(e) => handleDateChange('date_from', e.target.value)}
            />
          </div>
          <span className="document-filter__date-separator">~</span>
          <div className="document-filter__date-field">
            <label className="document-filter__date-label">종료일</label>
            <input
              type="date"
              className="document-filter__date-input"
              value={filters.date_to || ''}
              onChange={(e) => handleDateChange('date_to', e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div className="document-filter__summary">
          <span className="document-filter__summary-label">적용된 필터:</span>
          <div className="document-filter__tags">
            {filters.doc_types?.map((type) => {
              const option = DOC_TYPE_OPTIONS.find((o) => o.value === type);
              return (
                <span key={type} className="document-filter__tag">
                  {option?.label}
                  <button
                    className="document-filter__tag-remove"
                    onClick={() => handleDocTypeChange(type, false)}
                  >
                    ×
                  </button>
                </span>
              );
            })}
            {filters.statuses
              ?.filter((s) => s !== 'EMBEDDED' || (filters.statuses?.length || 0) > 1)
              .map((status) => {
                const option = STATUS_OPTIONS.find((o) => o.value === status);
                return (
                  <span key={status} className="document-filter__tag document-filter__tag--status">
                    {option?.label}
                    <button
                      className="document-filter__tag-remove"
                      onClick={() => handleStatusChange(status, false)}
                    >
                      ×
                    </button>
                  </span>
                );
              })}
            {filters.keyword && (
              <span className="document-filter__tag document-filter__tag--keyword">
                "{filters.keyword}"
                <button
                  className="document-filter__tag-remove"
                  onClick={() => {
                    setKeywordInput('');
                    onFilterChange({ ...filters, keyword: undefined });
                  }}
                >
                  ×
                </button>
              </span>
            )}
            {(filters.date_from || filters.date_to) && (
              <span className="document-filter__tag document-filter__tag--date">
                {filters.date_from || '시작'} ~ {filters.date_to || '종료'}
                <button
                  className="document-filter__tag-remove"
                  onClick={() =>
                    onFilterChange({
                      ...filters,
                      date_from: undefined,
                      date_to: undefined,
                    })
                  }
                >
                  ×
                </button>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentFilter;
