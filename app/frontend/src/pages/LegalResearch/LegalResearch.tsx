import React, { useState } from 'react';
import { FiSearch, FiFilter, FiBookOpen, FiBook, FiFileText, FiAlertCircle } from 'react-icons/fi';
import './LegalResearch.css';
import { apiClient } from '../../api/client';
import type { SearchResult, DocumentType } from '../../types';

const LegalResearch: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDataSources, setSelectedDataSources] = useState({
    cases: true,
    laws: true,
    interpretations: true,
    decisions: false
  });
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setError(null);

    try {
      // 선택된 데이터 소스 필터링
      const selectedTypes: DocumentType[] = [];
      if (selectedDataSources.cases) selectedTypes.push('case');
      if (selectedDataSources.laws) selectedTypes.push('law');
      if (selectedDataSources.interpretations) selectedTypes.push('interpretation');
      if (selectedDataSources.decisions) selectedTypes.push('decision');

      // 실제 백엔드 API 호출
      const results = await apiClient.search({
        query: searchQuery,
        filters: {
          types: selectedTypes
        },
        limit: 10
      });

      setSearchResults(results);
    } catch (err) {
      console.error('Search error:', err);
      setError(err instanceof Error ? err.message : '검색 중 오류가 발생했습니다.');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const toggleDataSource = (source: keyof typeof selectedDataSources) => {
    setSelectedDataSources(prev => ({
      ...prev,
      [source]: !prev[source]
    }));
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'case': return <FiBook />;
      case 'law': return <FiBookOpen />;
      case 'interpretation': return <FiFileText />;
      default: return <FiFileText />;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'case': return '판례';
      case 'law': return '법령';
      case 'interpretation': return '해석례';
      default: return '기타';
    }
  };

  return (
    <div className="legal-research">
      <div className="research-header">
        <h2>법률 리서치</h2>
        <p>AI 기반 법률 검색으로 빠르고 정확한 답변을 찾아보세요</p>
      </div>

      <form className="search-form" onSubmit={handleSearch}>
        <div className="search-input-wrapper">
          <FiSearch className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="예: 위법수집증거의 증거능력 판단 기준은?"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            autoFocus
          />
          <button
            type="submit"
            className="search-button"
            disabled={isSearching}
          >
            {isSearching ? '검색 중...' : '검색'}
          </button>
        </div>

        <div className="search-filters">
          <span className="filter-label">
            <FiFilter /> 데이터 소스:
          </span>
          <label className="filter-checkbox">
            <input
              type="checkbox"
              checked={selectedDataSources.cases}
              onChange={() => toggleDataSource('cases')}
            />
            <span>판례</span>
          </label>
          <label className="filter-checkbox">
            <input
              type="checkbox"
              checked={selectedDataSources.laws}
              onChange={() => toggleDataSource('laws')}
            />
            <span>법령</span>
          </label>
          <label className="filter-checkbox">
            <input
              type="checkbox"
              checked={selectedDataSources.interpretations}
              onChange={() => toggleDataSource('interpretations')}
            />
            <span>해석례</span>
          </label>
          <label className="filter-checkbox">
            <input
              type="checkbox"
              checked={selectedDataSources.decisions}
              onChange={() => toggleDataSource('decisions')}
            />
            <span>결정례</span>
          </label>
        </div>
      </form>

      {error && (
        <div className="search-error">
          <FiAlertCircle className="error-icon" />
          <div className="error-content">
            <h4>검색 오류</h4>
            <p>{error}</p>
            <button onClick={() => setError(null)} className="error-dismiss">
              닫기
            </button>
          </div>
        </div>
      )}

      {searchResults.length > 0 && (
        <div className="search-results">
          <div className="results-header">
            <h3>검색 결과 ({searchResults.length}건)</h3>
          </div>
          <div className="results-list">
            {searchResults.map(result => (
              <div key={result.id} className="result-card">
                <div className="result-header">
                  <div className="result-title-wrapper">
                    <span className="result-type-icon">{getTypeIcon(result.type)}</span>
                    <h4 className="result-title">{result.title}</h4>
                  </div>
                  <div className="result-meta">
                    <span className="result-type-label">{getTypeLabel(result.type)}</span>
                    <span className="result-relevance">{result.relevance}% 일치</span>
                  </div>
                </div>
                <p className="result-summary">{result.summary}</p>
                <div className="result-footer">
                  <span className="result-date">{result.date}</span>
                  {result.citation && (
                    <span className="result-citation">{result.citation}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {searchResults.length === 0 && !isSearching && (
        <div className="research-placeholder">
          <div className="placeholder-content">
            <FiSearch className="placeholder-icon" />
            <h3>법률 질문을 입력하세요</h3>
            <p>형사법 관련 판례, 법령, 해석례를 AI가 빠르게 찾아드립니다</p>
            <div className="example-queries">
              <h4>예시 질문:</h4>
              <ul>
                <li>"절도죄의 구성요건은?"</li>
                <li>"위법수집증거 배제 원칙의 예외는?"</li>
                <li>"음주운전 양형 기준"</li>
                <li>"정당방위 성립 요건"</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LegalResearch;