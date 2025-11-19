/**
 * Latest Precedents Fetcher Component
 * 최신 판례 가져오기 컴포넌트
 */

import React, { useState } from 'react';
import { fetchLatestPrecedents, FetchLatestResponse } from '../../services/precedentScrapingService';
import './LatestPrecedentsFetcher.css';

interface LatestPrecedentsFetcherProps {
  onFetchComplete?: (response: FetchLatestResponse) => void;
}

const LatestPrecedentsFetcher: React.FC<LatestPrecedentsFetcherProps> = ({ onFetchComplete }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 중복 요청 방지 플래그
  let isFetching = false;

  const handleFetchPrecedents = async () => {
    // 중복 요청 방지
    if (isFetching || loading) {
      console.log('Already fetching, skipping...');
      return;
    }

    isFetching = true;
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      console.log('Fetching latest 10 precedents');

      const response = await fetchLatestPrecedents(10);

      if (response.success) {
        setSuccess(
          `성공! ${response.fetched_count}건 조회, ${response.stored_count}건 저장되었습니다.`
        );

        // Callback 호출
        if (onFetchComplete) {
          onFetchComplete(response);
        }

        // 성공 메시지 3초 후 자동 제거
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(response.message || '판례를 가져오는데 실패했습니다.');
      }
    } catch (err: any) {
      console.error('Error fetching precedents:', err);
      setError(err.message || '판례를 가져오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
      isFetching = false;
    }
  };

  return (
    <div className="latest-precedents-fetcher">
      <div className="fetcher-controls">
        <button
          className={`fetch-button ${loading ? 'loading' : ''}`}
          onClick={handleFetchPrecedents}
          disabled={loading}
        >
          {loading ? (
            <>
              <span className="spinner"></span>
              가져오는 중...
            </>
          ) : (
            <>
              <span className="icon">🔄</span>
              최신 판례 10건 가져오기
            </>
          )}
        </button>
      </div>

      {/* 성공 메시지 */}
      {success && (
        <div className="message success-message">
          <span className="icon">✅</span>
          {success}
        </div>
      )}

      {/* 에러 메시지 */}
      {error && (
        <div className="message error-message">
          <span className="icon">❌</span>
          {error}
        </div>
      )}

      {/* 안내 메시지 */}
      <div className="info-message">
        <span className="icon">ℹ️</span>
        한 번에 최대 10건의 판례를 가져옵니다. (Rate limit: 1초)
      </div>
    </div>
  );
};

export default LatestPrecedentsFetcher;
