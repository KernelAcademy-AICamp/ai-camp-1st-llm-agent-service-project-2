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
      setError('판례를 불러오는데 실패했습니다.');
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
   * 판례 카드 클릭
   */
  const handlePrecedentClick = (precedentId: string) => {
    fetchPrecedentDetail(precedentId);
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
                  className="precedent-card"
                  onClick={() => handlePrecedentClick(precedent.id)}
                >
                  <div className="card-header">
                    <h3 className="case-number">{precedent.case_number}</h3>
                    <span className="case-type">{precedent.case_type}</span>
                  </div>
                  <h2 className="title">{precedent.title}</h2>
                  <p className="summary">
                    {precedent.summary
                      ? precedent.summary.substring(0, 150) + '...'
                      : '요약 정보가 없습니다.'}
                  </p>
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
