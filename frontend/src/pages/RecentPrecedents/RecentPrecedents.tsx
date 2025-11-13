/**
 * RecentPrecedents Component
 *
 * 최신 대법원 판례 목록을 표시하는 컴포넌트
 * - 카드 그리드 레이아웃
 * - 필터링 (날짜, 전문분야)
 * - 페이지네이션
 * - 판례 상세보기 모달
 * - 수동 새로고침 기능
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../../api/client';
import { Precedent, PrecedentDetail } from '../../types';
import './RecentPrecedents.css';

// 전문분야 옵션
const SPECIALIZATIONS = [
  '전체',
  '형사일반',
  '성범죄',
  '마약',
  '폭력',
  '사기',
  '교통사고',
  '횡령배임',
  '명예훼손',
  '위증',
  '뇌물',
];

// Mock 판례 데이터
const MOCK_PRECEDENTS: Precedent[] = [
  {
    id: 'mock-1',
    case_number: '2024도1234',
    title: '특수절도죄의 성립요건 및 야간주거침입절도와의 관계',
    summary: '피고인이 야간에 타인의 주거에 침입하여 재물을 절취한 경우, 특수절도죄와 야간주거침입절도죄의 성립요건 및 적용 관계에 대하여 판시한 사례',
    court: '대법원',
    decision_date: '2024-03-15',
    case_type: '형사',
    specialization_tags: ['형사일반', '절도'],
    case_link: null,
    created_at: '2024-03-15T00:00:00Z'
  },
  {
    id: 'mock-2',
    case_number: '2024도5678',
    title: '위법수집증거 배제법칙의 적용범위와 예외사유',
    summary: '수사기관이 영장 없이 수집한 증거의 증거능력 인정 여부 및 위법수집증거 배제법칙의 예외가 인정되는 경우',
    court: '대법원',
    decision_date: '2024-02-28',
    case_type: '형사',
    specialization_tags: ['형사일반', '증거법'],
    case_link: null,
    created_at: '2024-02-28T00:00:00Z'
  },
  {
    id: 'mock-3',
    case_number: '2024도2345',
    title: '성폭력범죄에서 피해자 진술의 신빙성 판단 기준',
    summary: '성폭력범죄에서 피해자의 진술이 유일한 증거인 경우, 그 진술의 신빙성을 판단하는 기준 및 방법',
    court: '대법원',
    decision_date: '2024-02-20',
    case_type: '형사',
    specialization_tags: ['성범죄'],
    case_link: null,
    created_at: '2024-02-20T00:00:00Z'
  },
  {
    id: 'mock-4',
    case_number: '2024도3456',
    title: '마약류 소지죄에서 소지의 의미 및 인식 필요성',
    summary: '마약류를 소지하였다는 이유로 기소된 사건에서, 소지의 의미와 피고인의 인식이 필요한지 여부',
    court: '대법원',
    decision_date: '2024-01-25',
    case_type: '형사',
    specialization_tags: ['마약'],
    case_link: null,
    created_at: '2024-01-25T00:00:00Z'
  },
  {
    id: 'mock-5',
    case_number: '2024도4567',
    title: '폭행죄와 상해죄의 구별 기준 및 고의의 내용',
    summary: '폭행 결과 상해가 발생한 경우 폭행죄와 상해죄를 구별하는 기준 및 상해의 고의 인정 여부',
    court: '대법원',
    decision_date: '2024-01-10',
    case_type: '형사',
    specialization_tags: ['폭력'],
    case_link: null,
    created_at: '2024-01-10T00:00:00Z'
  },
  {
    id: 'mock-6',
    case_number: '2023도9876',
    title: '사기죄에서 기망행위와 착오 사이의 인과관계',
    summary: '사기죄의 성립을 위해서는 기망행위와 피해자의 착오 사이에 인과관계가 있어야 하는지 여부',
    court: '대법원',
    decision_date: '2023-12-15',
    case_type: '형사',
    specialization_tags: ['사기'],
    case_link: null,
    created_at: '2023-12-15T00:00:00Z'
  },
  {
    id: 'mock-7',
    case_number: '2023도8765',
    title: '교통사고처리특례법상 중과실의 판단 기준',
    summary: '교통사고를 야기한 운전자에게 중과실이 인정되는지 여부를 판단하는 기준 및 고려 요소',
    court: '대법원',
    decision_date: '2023-11-30',
    case_type: '형사',
    specialization_tags: ['교통사고'],
    case_link: null,
    created_at: '2023-11-30T00:00:00Z'
  },
  {
    id: 'mock-8',
    case_number: '2023도7654',
    title: '업무상 횡령죄에서 불법영득의사의 인정 기준',
    summary: '업무상 횡령죄의 성립을 위해 필요한 불법영득의사가 인정되는 경우 및 판단 기준',
    court: '대법원',
    decision_date: '2023-10-20',
    case_type: '형사',
    specialization_tags: ['횡령배임'],
    case_link: null,
    created_at: '2023-10-20T00:00:00Z'
  },
  {
    id: 'mock-9',
    case_number: '2023도6543',
    title: '명예훼손죄에서 공공의 이익에 관한 사실 적시의 판단',
    summary: '명예훼손죄의 위법성조각사유로서 공공의 이익에 관한 사실 적시에 해당하는지 판단하는 기준',
    court: '대법원',
    decision_date: '2023-09-15',
    case_type: '형사',
    specialization_tags: ['명예훼손'],
    case_link: null,
    created_at: '2023-09-15T00:00:00Z'
  },
  {
    id: 'mock-10',
    case_number: '2023도5432',
    title: '위증죄에서 허위진술의 의미 및 중요사항 해당 여부',
    summary: '위증죄가 성립하기 위한 허위진술의 의미와 그것이 재판 결과에 영향을 미칠 수 있는 중요사항인지 판단하는 기준',
    court: '대법원',
    decision_date: '2023-08-25',
    case_type: '형사',
    specialization_tags: ['위증'],
    case_link: null,
    created_at: '2023-08-25T00:00:00Z'
  },
  {
    id: 'mock-11',
    case_number: '2023도4321',
    title: '뇌물죄에서 직무관련성 및 대가관계의 판단',
    summary: '공무원이 금품을 수수한 경우 뇌물죄가 성립하기 위한 직무관련성과 대가관계 인정 기준',
    court: '대법원',
    decision_date: '2023-07-10',
    case_type: '형사',
    specialization_tags: ['뇌물'],
    case_link: null,
    created_at: '2023-07-10T00:00:00Z'
  },
  {
    id: 'mock-12',
    case_number: '2023도3210',
    title: '정당방위의 성립요건 및 과잉방위의 판단',
    summary: '정당방위가 인정되기 위한 요건과 과잉방위에 해당하는지 여부를 판단하는 기준',
    court: '대법원',
    decision_date: '2023-06-20',
    case_type: '형사',
    specialization_tags: ['형사일반'],
    case_link: null,
    created_at: '2023-06-20T00:00:00Z'
  }
];

const RecentPrecedents: React.FC = () => {
  // State
  const [precedents, setPrecedents] = useState<Precedent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState<number>(0);

  // Pagination
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [itemsPerPage] = useState<number>(12);

  // Filters
  const [selectedSpecialization, setSelectedSpecialization] = useState<string>('전체');

  // Tab state
  const [activeTab, setActiveTab] = useState<'scourt' | 'vectordb'>('scourt');

  // Search
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searching, setSearching] = useState<boolean>(false);

  // Modal
  const [selectedPrecedent, setSelectedPrecedent] = useState<PrecedentDetail | null>(null);
  const [modalLoading, setModalLoading] = useState<boolean>(false);

  // Refresh state
  const [refreshing, setRefreshing] = useState<boolean>(false);

  /**
   * 판례 데이터 로드
   */
  const fetchPrecedents = async () => {
    try {
      setLoading(true);
      setError(null);

      const offset = (currentPage - 1) * itemsPerPage;

      let response;
      if (selectedSpecialization === '전체') {
        response = await apiClient.getRecentPrecedents(itemsPerPage, offset);
      } else {
        response = await apiClient.searchPrecedentsBySpecialization(
          selectedSpecialization,
          itemsPerPage,
          offset
        );
      }

      setPrecedents(response.precedents);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch precedents:', err);

      // API 실패 시 mock data 사용
      console.log('Using mock data as fallback');
      const filteredMockData = selectedSpecialization === '전체'
        ? MOCK_PRECEDENTS
        : MOCK_PRECEDENTS.filter(p => p.specialization_tags.includes(selectedSpecialization));

      const start = (currentPage - 1) * itemsPerPage;
      const end = start + itemsPerPage;
      setPrecedents(filteredMockData.slice(start, end));
      setTotal(filteredMockData.length);
      setError(null); // Clear error when using mock data
    } finally {
      setLoading(false);
    }
  };

  /**
   * 판례 상세 정보 로드
   */
  const fetchPrecedentDetail = async (precedentId: string) => {
    try {
      setModalLoading(true);
      const detail = await apiClient.getPrecedentDetail(precedentId);
      setSelectedPrecedent(detail);
    } catch (err) {
      console.error('Failed to fetch precedent detail:', err);
      alert('판례 상세 정보를 불러오는데 실패했습니다.');
    } finally {
      setModalLoading(false);
    }
  };

  /**
   * 탭별 검색 처리
   */
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      alert('검색어를 입력해주세요.');
      return;
    }

    if (activeTab === 'scourt') {
      // 대법원 크롤링 (10개)
      await handleScourtScrape();
    } else {
      // ChromaDB 벡터 검색 (20개)
      await handleVectorDBSearch();
    }
  };

  /**
   * DB 키워드 검색 (제목, 요약에서 검색)
   */
  const handleScourtScrape = async () => {
    try {
      setSearching(true);
      setError(null);

      const result = await apiClient.searchPrecedentsByKeyword(searchQuery, 20, 0);

      if (result.total > 0) {
        setPrecedents(result.precedents);
        setTotal(result.total);
        setCurrentPage(1);
      } else {
        alert(`"${searchQuery}" 키워드로 검색된 판례가 없습니다.`);
      }
    } catch (err) {
      console.error('DB keyword search error:', err);
      alert('DB 검색에 실패했습니다.');
    } finally {
      setSearching(false);
    }
  };

  /**
   * ChromaDB 벡터 검색 (20개)
   */
  const handleVectorDBSearch = async () => {
    try {
      setSearching(true);
      setError(null);

      const result = await apiClient.searchVectorDB(searchQuery, 20);

      if (result.success && result.total_count > 0) {
        // Convert VectorDB results to Precedent format
        const searchPrecedents: Precedent[] = result.results.map((r, idx) => ({
          id: `vectordb-${idx}`,
          case_number: r.case_number,
          title: r.title,
          summary: r.summary,
          court: r.court,
          decision_date: r.decision_date,
          case_type: '형사',
          specialization_tags: ['DB검색'],
          case_link: null,
          created_at: new Date().toISOString()
        }));

        setPrecedents(searchPrecedents);
        setTotal(searchPrecedents.length);
        setCurrentPage(1);
      } else {
        alert(result.message || 'DB에서 판례를 찾을 수 없습니다.');
      }
    } catch (err) {
      console.error('VectorDB search error:', err);
      alert('DB 검색에 실패했습니다.');
    } finally {
      setSearching(false);
    }
  };

  /**
   * 수동 새로고침 (서버에서 크롤링)
   */
  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      const result = await apiClient.refreshPrecedents(10);
      alert(`${result.stored_count}건의 새로운 판례가 추가되었습니다.`);
      await fetchPrecedents();
    } catch (err) {
      console.error('Failed to refresh precedents:', err);
      alert('판례 새로고침에 실패했습니다.');
    } finally {
      setRefreshing(false);
    }
  };

  /**
   * 전문분야 필터 변경
   */
  const handleSpecializationChange = (specialization: string) => {
    setSelectedSpecialization(specialization);
    setCurrentPage(1); // 필터 변경 시 첫 페이지로
  };

  /**
   * 페이지 변경
   */
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  /**
   * 판례 카드 클릭 - 외부 링크로 이동
   */
  const handlePrecedentClick = (caseLink: string | null) => {
    if (caseLink) {
      window.open(caseLink, '_blank', 'noopener,noreferrer');
    }
  };

  /**
   * 모달 닫기
   */
  const closeModal = () => {
    setSelectedPrecedent(null);
  };

  /**
   * 날짜 포맷팅
   */
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // 초기 로드 및 필터/페이지 변경 시 데이터 로드
  useEffect(() => {
    fetchPrecedents();
  }, [currentPage, selectedSpecialization]);

  // 총 페이지 수 계산
  const totalPages = Math.ceil(total / itemsPerPage);

  return (
    <div className="recent-precedents">
      {/* Header */}
      <div className="precedents-header">
        <div className="header-content">
          <h1>최신 대법원 판례</h1>
          <p className="subtitle">형사법 전문분야별 최신 판례를 확인하세요</p>
        </div>
        <button
          className="refresh-button"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? (
            <>
              <span className="spinner"></span>
              새로고침 중...
            </>
          ) : (
            <>
              <span className="icon">↻</span>
              새로고침
            </>
          )}
        </button>
      </div>

      {/* Search Section with Tabs */}
      <div className="search-section">
        {/* Tabs */}
        <div className="search-tabs">
          <button
            className={`tab ${activeTab === 'scourt' ? 'active' : ''}`}
            onClick={() => setActiveTab('scourt')}
          >
            DB 키워드 검색
          </button>
          <button
            className={`tab ${activeTab === 'vectordb' ? 'active' : ''}`}
            onClick={() => setActiveTab('vectordb')}
          >
            벡터 DB 검색
          </button>
        </div>

        {/* Search Form */}
        <form className="search-form" onSubmit={handleSearch}>
          <div className="search-input-wrapper">
            <input
              type="text"
              className="search-input"
              placeholder={
                activeTab === 'scourt'
                  ? '키워드 입력 (예: 절도, 사기, 폭행) - 제목과 요약에서 검색'
                  : 'ChromaDB에서 판례 검색 (예: 절도죄, 위법수집증거, 정당방위)'
              }
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button
              type="submit"
              className="search-button"
              disabled={searching}
            >
              {searching ? (
                <>
                  <span className="spinner"></span>
                  검색 중...
                </>
              ) : (
                <>
                  <span className="icon">
                    {activeTab === 'scourt' ? '🔍' : '📚'}
                  </span>
                  {activeTab === 'scourt' ? 'DB에서 검색' : '벡터 DB 검색'}
                </>
              )}
            </button>
          </div>
        </form>

        {/* Info Notice */}
        <div className="search-notice">
          <span className="icon">ℹ️</span>
          {activeTab === 'scourt'
            ? '저장된 판례 DB에서 제목과 요약에 키워드가 포함된 판례를 검색합니다.'
            : 'ChromaDB에서 입력한 키워드와 의미적으로 유사한 판례를 최대 20개 검색합니다.'}
        </div>
      </div>

      {/* Filters */}
      <div className="precedents-filters">
        <div className="filter-group">
          <label>전문분야</label>
          <div className="specialization-tags">
            {SPECIALIZATIONS.map((spec) => (
              <button
                key={spec}
                className={`tag ${selectedSpecialization === spec ? 'active' : ''}`}
                onClick={() => handleSpecializationChange(spec)}
              >
                {spec}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Results Count */}
      <div className="results-info">
        <p>총 <strong>{total}</strong>건의 판례</p>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="loading-container">
          <div className="spinner large"></div>
          <p>판례를 불러오는 중...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="error-container">
          <p className="error-message">{error}</p>
          <button onClick={fetchPrecedents}>다시 시도</button>
        </div>
      )}

      {/* Precedents Grid */}
      {!loading && !error && (
        <>
          {precedents.length === 0 ? (
            <div className="empty-state">
              <p>판례가 없습니다.</p>
              <button onClick={handleRefresh}>새로고침</button>
            </div>
          ) : (
            <div className="precedents-grid">
              {precedents.map((precedent) => (
                <div
                  key={precedent.id}
                  className={`precedent-card ${precedent.case_link ? '' : 'no-link'}`}
                  onClick={() => handlePrecedentClick(precedent.case_link)}
                  style={{ cursor: precedent.case_link ? 'pointer' : 'default' }}
                >
                  <div className="card-header">
                    <h3 className="case-number">{precedent.case_number}</h3>
                    <span className="case-type">{precedent.case_type}</span>
                  </div>
                  <h2 className="title">{precedent.title}</h2>
                  <div className="card-footer">
                    <div className="tags">
                      {precedent.specialization_tags.slice(0, 3).map((tag, index) => (
                        <span key={index} className="tag">
                          {tag}
                        </span>
                      ))}
                    </div>
                    <div className="meta">
                      <span className="court">{precedent.court}</span>
                      <span className="date">{formatDate(precedent.decision_date)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="page-button"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                이전
              </button>
              <div className="page-numbers">
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter(
                    (page) =>
                      page === 1 ||
                      page === totalPages ||
                      (page >= currentPage - 2 && page <= currentPage + 2)
                  )
                  .map((page, index, array) => (
                    <React.Fragment key={page}>
                      {index > 0 && array[index - 1] !== page - 1 && (
                        <span className="ellipsis">...</span>
                      )}
                      <button
                        className={`page-number ${currentPage === page ? 'active' : ''}`}
                        onClick={() => handlePageChange(page)}
                      >
                        {page}
                      </button>
                    </React.Fragment>
                  ))}
              </div>
              <button
                className="page-button"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                다음
              </button>
            </div>
          )}
        </>
      )}

      {/* Detail Modal */}
      {selectedPrecedent && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal}>
              ✕
            </button>
            {modalLoading ? (
              <div className="modal-loading">
                <div className="spinner"></div>
                <p>상세 정보를 불러오는 중...</p>
              </div>
            ) : (
              <>
                <div className="modal-header">
                  <h2>{selectedPrecedent.title}</h2>
                  <div className="modal-meta">
                    <span className="case-number">{selectedPrecedent.case_number}</span>
                    <span className="court">{selectedPrecedent.court}</span>
                    <span className="date">{formatDate(selectedPrecedent.decision_date)}</span>
                  </div>
                </div>
                <div className="modal-body">
                  <div className="section">
                    <h3>전문분야</h3>
                    <div className="tags">
                      {selectedPrecedent.specialization_tags.map((tag, index) => (
                        <span key={index} className="tag">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  {selectedPrecedent.summary && (
                    <div className="section">
                      <h3>요약</h3>
                      <p className="summary-text">{selectedPrecedent.summary}</p>
                    </div>
                  )}
                  {selectedPrecedent.full_text && (
                    <div className="section">
                      <h3>판결문</h3>
                      <div className="full-text">{selectedPrecedent.full_text}</div>
                    </div>
                  )}
                  {selectedPrecedent.citation && (
                    <div className="section">
                      <h3>인용</h3>
                      <p className="citation">{selectedPrecedent.citation}</p>
                    </div>
                  )}
                  {selectedPrecedent.case_link && (
                    <div className="section">
                      <a
                        href={selectedPrecedent.case_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="external-link"
                      >
                        법률 공공포털에서 보기 →
                      </a>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default RecentPrecedents;
