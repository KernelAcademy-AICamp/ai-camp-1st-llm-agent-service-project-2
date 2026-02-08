/**
 * DocumentFilter Component (Session 13-C)
 *
 * RAG 검색 필터 패널 컴포넌트
 * - 문서 타입 필터 (계약서, 사건, 법령, 기타)
 * - 검색 기록
 */

import React, { useCallback, useMemo } from 'react';
import { FiFilter, FiChevronLeft, FiChevronRight, FiX, FiClock, FiTrash2 } from 'react-icons/fi';
import {
  RAGFilterOptions,
  UserDocumentType,
  UserDocumentStatus,
  SearchHistoryItem,
} from '../../types';
import { formatSearchDate } from '../../utils/searchHistory';
import './DocumentFilter.css';

interface DocumentFilterProps {
  filters: RAGFilterOptions;
  onFilterChange: (filters: RAGFilterOptions) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  isAdmin?: boolean;  // Admin-only features flag
  // Search history props
  searchHistory?: SearchHistoryItem[];
  onHistoryItemClick?: (item: SearchHistoryItem) => void;
  onHistoryItemDelete?: (itemId: string) => void;
  onClearHistory?: () => void;
}

// Document type options
const DOC_TYPE_OPTIONS: { value: UserDocumentType; label: string }[] = [
  { value: 'CONTRACT', label: '계약서' },
  { value: 'CASE', label: '사건' },
  { value: 'STATUTE', label: '법령' },
  { value: 'PRECEDENT', label: '판례' },
  { value: 'OTHER', label: '기타' },
];

// Document status options (Admin only)
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
  isAdmin = false,
  searchHistory = [],
  onHistoryItemClick,
  onHistoryItemDelete,
  onClearHistory,
}) => {

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

  // Handle status checkbox change (Admin only)
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

  // Clear all filters
  const handleClearAll = useCallback(() => {
    onFilterChange(
      isAdmin
        ? { statuses: ['EMBEDDED'] } // Admin: keep default status
        : {} // Regular user: clear all filters
    );
  }, [onFilterChange, isAdmin]);

  // Check if any filters are active
  const hasActiveFilters =
    (filters.doc_types && filters.doc_types.length > 0) ||
    (isAdmin && filters.statuses &&
      !(filters.statuses.length === 1 && filters.statuses[0] === 'EMBEDDED'));

  // Count active filters for badge display
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.doc_types && filters.doc_types.length > 0) {
      count += filters.doc_types.length;
    }
    if (isAdmin && filters.statuses) {
      // Don't count default EMBEDDED status
      const nonDefaultStatuses = filters.statuses.filter(s => s !== 'EMBEDDED');
      count += nonDefaultStatuses.length;
      // If only EMBEDDED is selected and there are other statuses available, count it
      if (filters.statuses.length > 1 || (filters.statuses.length === 1 && filters.statuses[0] !== 'EMBEDDED')) {
        count = filters.statuses.length;
      }
    }
    return count;
  }, [filters, isAdmin]);

  if (isCollapsed) {
    return (
      <div className="document-filter document-filter--collapsed">
        <button
          className="document-filter__toggle"
          onClick={onToggleCollapse}
          title="필터 패널 열기"
        >
          <div className="document-filter__toggle-section">
            <FiFilter className="document-filter__toggle-icon" />
            <span className="document-filter__toggle-label">필터</span>
            {activeFilterCount > 0 && (
              <span className="document-filter__badge document-filter__badge--inline">{activeFilterCount}</span>
            )}
          </div>
          <div className="document-filter__toggle-section">
            <FiClock className="document-filter__toggle-icon" />
            <span className="document-filter__toggle-label">검색 기록</span>
            {searchHistory.length > 0 && (
              <span className="document-filter__badge document-filter__badge--inline document-filter__badge--history">{searchHistory.length}</span>
            )}
          </div>
          <FiChevronRight className="document-filter__toggle-arrow" />
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
              <FiChevronLeft />
            </button>
          )}
        </div>
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

      {/* Document Status Filter (Admin Only) */}
      {isAdmin && (
        <div className="document-filter__section">
          <label className="document-filter__label">
            문서 상태 <span className="document-filter__admin-badge">(관리자 전용)</span>
          </label>
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
      )}

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
            {isAdmin && filters.statuses
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
          </div>
        </div>
      )}

      {/* Search History Section */}
      {searchHistory.length > 0 && (
        <div className="document-filter__history">
          <div className="document-filter__history-header">
            <span className="document-filter__history-title">
              <FiClock className="document-filter__history-icon" />
              검색 기록
            </span>
            {onClearHistory && (
              <button
                className="document-filter__history-clear"
                onClick={onClearHistory}
                title="검색 기록 전체 삭제"
              >
                <FiTrash2 />
              </button>
            )}
          </div>
          <div className="document-filter__history-list-container">
            <ul className="document-filter__history-list">
              {searchHistory.map((item) => (
                <li key={item.id} className="document-filter__history-item">
                  <button
                    className="document-filter__history-query"
                    onClick={() => onHistoryItemClick?.(item)}
                    title={`${item.query}\n${formatSearchDate(item.timestamp)}`}
                  >
                    <span className="document-filter__history-text">
                      {item.query.length > 25 ? item.query.slice(0, 25) + '...' : item.query}
                    </span>
                    <span className="document-filter__history-time">
                      {formatSearchDate(item.timestamp)}
                    </span>
                  </button>
                  {onHistoryItemDelete && (
                    <button
                      className="document-filter__history-delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        onHistoryItemDelete(item.id);
                      }}
                      title="삭제"
                    >
                      <FiX />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentFilter;
