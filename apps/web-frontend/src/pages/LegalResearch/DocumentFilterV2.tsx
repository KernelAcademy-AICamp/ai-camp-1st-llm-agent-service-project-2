/**
 * DocumentFilterV2 Component (Phase 4)
 *
 * 형사법 특화 검색 필터 패널 컴포넌트
 * - 문서 타입 필터 (계약서, 사건, 법령, 판례, 기타)
 * - 범죄 유형 필터 (절도, 사기, 폭행 등)
 * - 법원 필터 (대법원, 고등법원, 지방법원)
 * - 판결 유형 필터 (실형, 집행유예, 벌금, 무죄)
 * - 검색 기록
 */

import React, { useCallback, useMemo, useState } from 'react';
import {
  FiFilter,
  FiChevronLeft,
  FiChevronRight,
  FiX,
  FiClock,
  FiTrash2,
  FiChevronDown,
  FiChevronUp,
} from 'react-icons/fi';
import {
  RAGFilterOptions,
  UserDocumentType,
  UserDocumentStatus,
  SearchHistoryItem,
  CrimeType,
  CourtLevel,
  SentenceType,
} from '../../types';
import { formatSearchDate } from '../../utils/searchHistory';
import './DocumentFilterV2.css';

interface DocumentFilterV2Props {
  filters: RAGFilterOptions;
  onFilterChange: (filters: RAGFilterOptions) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  isAdmin?: boolean;
  // Search history props
  searchHistory?: SearchHistoryItem[];
  onHistoryItemClick?: (item: SearchHistoryItem) => void;
  onHistoryItemDelete?: (itemId: string) => void;
  onClearHistory?: () => void;
  // Criminal law mode
  enableCriminalFilters?: boolean;
  // Show/hide filters (only show search history when false)
  showFilters?: boolean;
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

// 범죄 유형 옵션 (형사법 특화)
const CRIME_TYPE_OPTIONS: { value: CrimeType; label: string; icon: string }[] = [
  { value: 'theft', label: '절도', icon: '🔓' },
  { value: 'fraud', label: '사기', icon: '💰' },
  { value: 'assault', label: '폭행/상해', icon: '👊' },
  { value: 'murder', label: '살인', icon: '⚠️' },
  { value: 'drug', label: '마약', icon: '💊' },
  { value: 'sex_crime', label: '성범죄', icon: '🚫' },
  { value: 'embezzlement', label: '횡령/배임', icon: '📊' },
  { value: 'dui', label: '음주운전', icon: '🚗' },
];

// 법원 레벨 옵션
const COURT_LEVEL_OPTIONS: { value: CourtLevel; label: string }[] = [
  { value: 'supreme', label: '대법원' },
  { value: 'high', label: '고등법원' },
  { value: 'district', label: '지방법원' },
];

// 판결 유형 옵션
const SENTENCE_TYPE_OPTIONS: { value: SentenceType; label: string; color: string }[] = [
  { value: 'imprisonment', label: '유죄 (실형)', color: '#ef4444' },
  { value: 'suspended', label: '유죄 (집행유예)', color: '#f59e0b' },
  { value: 'fine', label: '벌금형', color: '#3b82f6' },
  { value: 'acquittal', label: '무죄', color: '#10b981' },
];

const DocumentFilterV2: React.FC<DocumentFilterV2Props> = ({
  filters,
  onFilterChange,
  isCollapsed = false,
  onToggleCollapse,
  isAdmin = false,
  searchHistory = [],
  onHistoryItemClick,
  onHistoryItemDelete,
  onClearHistory,
  enableCriminalFilters = true,
  showFilters = true,  // 기본값 true (필터 표시)
}) => {
  // 섹션 펼침/접힘 상태
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    docType: true,
    crimeType: true,
    court: false,
    sentence: false,
    status: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // Handle document type checkbox change
  const handleDocTypeChange = useCallback(
    (docType: UserDocumentType, checked: boolean) => {
      const currentTypes = filters.doc_types || [];
      const newTypes = checked
        ? [...currentTypes, docType]
        : currentTypes.filter((t) => t !== docType);

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
      const newStatuses = checked
        ? [...currentStatuses, status]
        : currentStatuses.filter((s) => s !== status);

      onFilterChange({
        ...filters,
        statuses: newStatuses.length > 0 ? newStatuses : undefined,
      });
    },
    [filters, onFilterChange]
  );

  // Handle crime type filter change
  const handleCrimeTypeChange = useCallback(
    (crimeType: CrimeType, checked: boolean) => {
      const currentTypes = filters.crime_types || [];
      const newTypes = checked
        ? [...currentTypes, crimeType]
        : currentTypes.filter((t) => t !== crimeType);

      onFilterChange({
        ...filters,
        crime_types: newTypes.length > 0 ? newTypes : undefined,
      });
    },
    [filters, onFilterChange]
  );

  // Handle court level filter change
  const handleCourtLevelChange = useCallback(
    (courtLevel: CourtLevel, checked: boolean) => {
      const currentLevels = filters.court_level || [];
      const newLevels = checked
        ? [...currentLevels, courtLevel]
        : currentLevels.filter((l) => l !== courtLevel);

      onFilterChange({
        ...filters,
        court_level: newLevels.length > 0 ? newLevels : undefined,
      });
    },
    [filters, onFilterChange]
  );

  // Handle sentence type filter change
  const handleSentenceTypeChange = useCallback(
    (sentenceType: SentenceType, checked: boolean) => {
      const currentTypes = filters.sentence_type || [];
      const newTypes = checked
        ? [...currentTypes, sentenceType]
        : currentTypes.filter((t) => t !== sentenceType);

      onFilterChange({
        ...filters,
        sentence_type: newTypes.length > 0 ? newTypes : undefined,
      });
    },
    [filters, onFilterChange]
  );

  // Clear all filters
  const handleClearAll = useCallback(() => {
    onFilterChange(
      isAdmin ? { statuses: ['EMBEDDED'] } : {}
    );
  }, [onFilterChange, isAdmin]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return (
      (filters.doc_types && filters.doc_types.length > 0) ||
      (filters.crime_types && filters.crime_types.length > 0) ||
      (filters.court_level && filters.court_level.length > 0) ||
      (filters.sentence_type && filters.sentence_type.length > 0) ||
      (isAdmin &&
        filters.statuses &&
        !(filters.statuses.length === 1 && filters.statuses[0] === 'EMBEDDED'))
    );
  }, [filters, isAdmin]);

  // Count active filters for badge display
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.doc_types) count += filters.doc_types.length;
    if (filters.crime_types) count += filters.crime_types.length;
    if (filters.court_level) count += filters.court_level.length;
    if (filters.sentence_type) count += filters.sentence_type.length;
    if (isAdmin && filters.statuses) {
      const nonDefault = filters.statuses.filter((s) => s !== 'EMBEDDED');
      count += nonDefault.length;
    }
    return count;
  }, [filters, isAdmin]);

  // Collapsed view
  if (isCollapsed) {
    return (
      <div className="document-filter-v2 document-filter-v2--collapsed">
        <button
          className="document-filter-v2__toggle"
          onClick={onToggleCollapse}
          title={showFilters ? "필터 패널 열기" : "검색 기록 열기"}
        >
          {/* 필터 섹션 - showFilters가 true일 때만 표시 */}
          {showFilters && (
            <div className="document-filter-v2__toggle-section">
              <FiFilter className="document-filter-v2__toggle-icon" />
              <span className="document-filter-v2__toggle-label">필터</span>
              {activeFilterCount > 0 && (
                <span className="document-filter-v2__badge document-filter-v2__badge--inline">
                  {activeFilterCount}
                </span>
              )}
            </div>
          )}
          {/* 검색 기록 섹션 - 항상 표시 */}
          <div className="document-filter-v2__toggle-section">
            <FiClock className="document-filter-v2__toggle-icon" />
            <span className="document-filter-v2__toggle-label">검색 기록</span>
            {searchHistory.length > 0 && (
              <span className="document-filter-v2__badge document-filter-v2__badge--inline document-filter-v2__badge--history">
                {searchHistory.length}
              </span>
            )}
          </div>
          <FiChevronRight className="document-filter-v2__toggle-arrow" />
        </button>
      </div>
    );
  }

  return (
    <div className="document-filter-v2">
      {/* Header */}
      <div className="document-filter-v2__header">
        <h3 className="document-filter-v2__title">{showFilters ? '검색 필터' : '검색 기록'}</h3>
        <div className="document-filter-v2__actions">
          {showFilters && hasActiveFilters && (
            <button
              className="document-filter-v2__clear-btn"
              onClick={handleClearAll}
              title="필터 초기화"
            >
              초기화
            </button>
          )}
          {onToggleCollapse && (
            <button
              className="document-filter-v2__collapse-btn"
              onClick={onToggleCollapse}
              title="패널 접기"
            >
              <FiChevronLeft />
            </button>
          )}
        </div>
      </div>

      {/* Scrollable Content - showFilters가 true일 때만 표시 */}
      {showFilters && (
      <div className="document-filter-v2__content">
        {/* Document Type Filter */}
        <div className="document-filter-v2__section">
          <button
            className="document-filter-v2__section-header"
            onClick={() => toggleSection('docType')}
          >
            <span className="document-filter-v2__label">문서 유형</span>
            {expandedSections.docType ? <FiChevronUp /> : <FiChevronDown />}
          </button>
          {expandedSections.docType && (
            <div className="document-filter-v2__chips">
              {DOC_TYPE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  className={`document-filter-v2__chip ${
                    filters.doc_types?.includes(option.value) ? 'document-filter-v2__chip--active' : ''
                  }`}
                  onClick={() =>
                    handleDocTypeChange(
                      option.value,
                      !filters.doc_types?.includes(option.value)
                    )
                  }
                >
                  {option.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Crime Type Filter (형사법 특화) */}
        {enableCriminalFilters && (
          <div className="document-filter-v2__section document-filter-v2__section--criminal">
            <button
              className="document-filter-v2__section-header"
              onClick={() => toggleSection('crimeType')}
            >
              <span className="document-filter-v2__label">
                범죄 유형
                <span className="document-filter-v2__label-badge">형사</span>
              </span>
              {expandedSections.crimeType ? <FiChevronUp /> : <FiChevronDown />}
            </button>
            {expandedSections.crimeType && (
              <div className="document-filter-v2__chips document-filter-v2__chips--crime">
                {CRIME_TYPE_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    className={`document-filter-v2__chip document-filter-v2__chip--crime ${
                      filters.crime_types?.includes(option.value)
                        ? 'document-filter-v2__chip--active'
                        : ''
                    }`}
                    onClick={() =>
                      handleCrimeTypeChange(
                        option.value,
                        !filters.crime_types?.includes(option.value)
                      )
                    }
                    title={option.label}
                  >
                    <span className="document-filter-v2__chip-icon">{option.icon}</span>
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Court Level Filter */}
        {enableCriminalFilters && (
          <div className="document-filter-v2__section">
            <button
              className="document-filter-v2__section-header"
              onClick={() => toggleSection('court')}
            >
              <span className="document-filter-v2__label">법원</span>
              {expandedSections.court ? <FiChevronUp /> : <FiChevronDown />}
            </button>
            {expandedSections.court && (
              <div className="document-filter-v2__chips">
                {COURT_LEVEL_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    className={`document-filter-v2__chip ${
                      filters.court_level?.includes(option.value)
                        ? 'document-filter-v2__chip--active'
                        : ''
                    }`}
                    onClick={() =>
                      handleCourtLevelChange(
                        option.value,
                        !filters.court_level?.includes(option.value)
                      )
                    }
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Sentence Type Filter */}
        {enableCriminalFilters && (
          <div className="document-filter-v2__section">
            <button
              className="document-filter-v2__section-header"
              onClick={() => toggleSection('sentence')}
            >
              <span className="document-filter-v2__label">판결 유형</span>
              {expandedSections.sentence ? <FiChevronUp /> : <FiChevronDown />}
            </button>
            {expandedSections.sentence && (
              <div className="document-filter-v2__chips">
                {SENTENCE_TYPE_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    className={`document-filter-v2__chip document-filter-v2__chip--sentence ${
                      filters.sentence_type?.includes(option.value)
                        ? 'document-filter-v2__chip--active'
                        : ''
                    }`}
                    onClick={() =>
                      handleSentenceTypeChange(
                        option.value,
                        !filters.sentence_type?.includes(option.value)
                      )
                    }
                    style={{
                      '--chip-color': option.color,
                    } as React.CSSProperties}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Document Status Filter (Admin Only) */}
        {isAdmin && (
          <div className="document-filter-v2__section">
            <button
              className="document-filter-v2__section-header"
              onClick={() => toggleSection('status')}
            >
              <span className="document-filter-v2__label">
                문서 상태
                <span className="document-filter-v2__admin-badge">관리자</span>
              </span>
              {expandedSections.status ? <FiChevronUp /> : <FiChevronDown />}
            </button>
            {expandedSections.status && (
              <div className="document-filter-v2__checkbox-group">
                {STATUS_OPTIONS.map((option) => (
                  <label key={option.value} className="document-filter-v2__checkbox">
                    <input
                      type="checkbox"
                      checked={filters.statuses?.includes(option.value) || false}
                      onChange={(e) =>
                        handleStatusChange(option.value, e.target.checked)
                      }
                    />
                    <span className="document-filter-v2__checkbox-label">
                      {option.label}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Active Filters Summary */}
        {hasActiveFilters && (
          <div className="document-filter-v2__summary">
            <span className="document-filter-v2__summary-label">적용된 필터:</span>
            <div className="document-filter-v2__tags">
              {/* Doc types */}
              {filters.doc_types?.map((type) => {
                const option = DOC_TYPE_OPTIONS.find((o) => o.value === type);
                return (
                  <span key={`doc-${type}`} className="document-filter-v2__tag">
                    {option?.label}
                    <button
                      className="document-filter-v2__tag-remove"
                      onClick={() => handleDocTypeChange(type, false)}
                    >
                      <FiX />
                    </button>
                  </span>
                );
              })}
              {/* Crime types */}
              {filters.crime_types?.map((type) => {
                const option = CRIME_TYPE_OPTIONS.find((o) => o.value === type);
                return (
                  <span
                    key={`crime-${type}`}
                    className="document-filter-v2__tag document-filter-v2__tag--crime"
                  >
                    {option?.icon} {option?.label}
                    <button
                      className="document-filter-v2__tag-remove"
                      onClick={() => handleCrimeTypeChange(type, false)}
                    >
                      <FiX />
                    </button>
                  </span>
                );
              })}
              {/* Court levels */}
              {filters.court_level?.map((level) => {
                const option = COURT_LEVEL_OPTIONS.find((o) => o.value === level);
                return (
                  <span
                    key={`court-${level}`}
                    className="document-filter-v2__tag document-filter-v2__tag--court"
                  >
                    {option?.label}
                    <button
                      className="document-filter-v2__tag-remove"
                      onClick={() => handleCourtLevelChange(level, false)}
                    >
                      <FiX />
                    </button>
                  </span>
                );
              })}
              {/* Sentence types */}
              {filters.sentence_type?.map((type) => {
                const option = SENTENCE_TYPE_OPTIONS.find((o) => o.value === type);
                return (
                  <span
                    key={`sentence-${type}`}
                    className="document-filter-v2__tag document-filter-v2__tag--sentence"
                    style={{ '--tag-color': option?.color } as React.CSSProperties}
                  >
                    {option?.label}
                    <button
                      className="document-filter-v2__tag-remove"
                      onClick={() => handleSentenceTypeChange(type, false)}
                    >
                      <FiX />
                    </button>
                  </span>
                );
              })}
              {/* Admin statuses */}
              {isAdmin &&
                filters.statuses
                  ?.filter((s) => s !== 'EMBEDDED' || (filters.statuses?.length || 0) > 1)
                  .map((status) => {
                    const option = STATUS_OPTIONS.find((o) => o.value === status);
                    return (
                      <span
                        key={`status-${status}`}
                        className="document-filter-v2__tag document-filter-v2__tag--status"
                      >
                        {option?.label}
                        <button
                          className="document-filter-v2__tag-remove"
                          onClick={() => handleStatusChange(status, false)}
                        >
                          <FiX />
                        </button>
                      </span>
                    );
                  })}
            </div>
          </div>
        )}
      </div>
      )}

      {/* Search History Section */}
      {searchHistory.length > 0 && (
        <div className="document-filter-v2__history">
          <div className="document-filter-v2__history-header">
            <span className="document-filter-v2__history-title">
              <FiClock className="document-filter-v2__history-icon" />
              검색 기록
            </span>
            {onClearHistory && (
              <button
                className="document-filter-v2__history-clear"
                onClick={onClearHistory}
                title="검색 기록 전체 삭제"
              >
                <FiTrash2 />
              </button>
            )}
          </div>
          <div className="document-filter-v2__history-list-container">
            <ul className="document-filter-v2__history-list">
              {searchHistory.map((item) => (
                <li key={item.id} className="document-filter-v2__history-item">
                  <button
                    className="document-filter-v2__history-query"
                    onClick={() => onHistoryItemClick?.(item)}
                    title={`${item.query}\n${formatSearchDate(item.timestamp)}`}
                  >
                    <span className="document-filter-v2__history-text">
                      {item.query.length > 25 ? item.query.slice(0, 25) + '...' : item.query}
                    </span>
                    <span className="document-filter-v2__history-time">
                      {formatSearchDate(item.timestamp)}
                    </span>
                  </button>
                  {onHistoryItemDelete && (
                    <button
                      className="document-filter-v2__history-delete"
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

export default DocumentFilterV2;
