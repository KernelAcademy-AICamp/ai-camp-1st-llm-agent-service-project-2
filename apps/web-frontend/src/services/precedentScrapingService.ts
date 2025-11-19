/**
 * Precedent Scraping Service
 * 대법원 포털 스크래핑 API 클라이언트
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface FetchLatestRequest {
  limit: number;
}

export interface FetchByKeywordRequest {
  keyword: string;
  limit: number;
}

export interface FetchLatestResponse {
  success: boolean;
  message: string;
  fetched_count: number;
  stored_count: number;
  precedents: Array<{
    case_number: string;
    title: string;
    court: string;
    decision_date: string;
  }>;
}

/**
 * 최신 판례 가져오기 (최대 10건)
 */
export const fetchLatestPrecedents = async (
  limit: number = 10
): Promise<FetchLatestResponse> => {
  // Hard limit enforcement
  if (limit > 10) {
    console.warn(`Limit ${limit} exceeds maximum of 10, capping at 10`);
    limit = 10;
  }

  const response = await fetch(`${API_BASE_URL}/api/precedents/fetch-latest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      limit,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
};

/**
 * 키워드로 최신 판례 검색 (1개)
 */
export const fetchPrecedentByKeyword = async (
  keyword: string,
  limit: number = 1
): Promise<FetchLatestResponse> => {
  // Hard limit enforcement
  if (limit > 1) {
    console.warn(`Limit ${limit} exceeds maximum of 1, capping at 1`);
    limit = 1;
  }

  const response = await fetch(`${API_BASE_URL}/api/precedents/search-keyword`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      keyword,
      limit,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
};

/**
 * 스크래핑 상태 조회
 */
export const getScrapingStatus = async (): Promise<{
  status: string;
  message: string;
}> => {
  const response = await fetch(`${API_BASE_URL}/api/precedents/scraping-status`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};
