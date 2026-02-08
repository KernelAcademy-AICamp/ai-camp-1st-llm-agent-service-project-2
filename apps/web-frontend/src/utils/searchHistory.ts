/**
 * Search History Utilities
 *
 * 검색 기록을 localStorage에 저장하고 관리하는 유틸리티
 * - 사용자별 검색 기록 저장 (userId 기반)
 * - 최대 50개 기록 유지
 * - 새로고침/탭 이동 시에도 유지
 */

import { SearchHistoryItem, RAGFilterOptions } from '../types';

const STORAGE_KEY_PREFIX = 'lawlaw_search_history';
const MAX_HISTORY_ITEMS = 50;

/**
 * 사용자별 스토리지 키 생성
 */
const getStorageKey = (userId?: string): string => {
  return userId ? `${STORAGE_KEY_PREFIX}_${userId}` : `${STORAGE_KEY_PREFIX}_anonymous`;
};

/**
 * 검색 기록 가져오기
 */
export const getSearchHistory = (userId?: string): SearchHistoryItem[] => {
  try {
    const key = getStorageKey(userId);
    const stored = localStorage.getItem(key);
    if (!stored) return [];

    const parsed = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.error('Failed to load search history:', error);
    return [];
  }
};

/**
 * 검색 기록 저장
 */
export const saveSearchHistory = (history: SearchHistoryItem[], userId?: string): void => {
  try {
    const key = getStorageKey(userId);
    localStorage.setItem(key, JSON.stringify(history));
  } catch (error) {
    console.error('Failed to save search history:', error);
  }
};

/**
 * 새 검색 기록 추가
 */
export const addSearchHistoryItem = (
  query: string,
  topK: number,
  responseMode: 'auto' | 'concise' | 'standard' | 'detailed',
  filters?: RAGFilterOptions,
  sourceCount?: number,
  userId?: string
): SearchHistoryItem => {
  const history = getSearchHistory(userId);

  // 동일한 쿼리가 이미 있으면 제거 (최신으로 업데이트)
  const filteredHistory = history.filter(
    (item) => item.query.trim().toLowerCase() !== query.trim().toLowerCase()
  );

  const newItem: SearchHistoryItem = {
    id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    query: query.trim(),
    timestamp: new Date().toISOString(),
    topK,
    responseMode,
    filters,
    sourceCount,
  };

  // 새 항목을 맨 앞에 추가하고 최대 개수 유지
  const updatedHistory = [newItem, ...filteredHistory].slice(0, MAX_HISTORY_ITEMS);

  saveSearchHistory(updatedHistory, userId);
  return newItem;
};

/**
 * 특정 검색 기록 삭제
 */
export const removeSearchHistoryItem = (itemId: string, userId?: string): void => {
  const history = getSearchHistory(userId);
  const filteredHistory = history.filter((item) => item.id !== itemId);
  saveSearchHistory(filteredHistory, userId);
};

/**
 * 모든 검색 기록 초기화
 */
export const clearSearchHistory = (userId?: string): void => {
  const key = getStorageKey(userId);
  localStorage.removeItem(key);
};

/**
 * 검색 기록 날짜 포맷팅
 */
export const formatSearchDate = (timestamp: string): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (minutes < 1) return '방금 전';
  if (minutes < 60) return `${minutes}분 전`;
  if (hours < 24) return `${hours}시간 전`;
  if (days < 7) return `${days}일 전`;

  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

/**
 * 사용자 로그인 시 검색 기록 마이그레이션
 * anonymous 기록을 사용자 기록으로 병합
 */
export const migrateAnonymousHistory = (userId: string): void => {
  const anonymousHistory = getSearchHistory();
  const userHistory = getSearchHistory(userId);

  if (anonymousHistory.length === 0) return;

  // 사용자 기록에 anonymous 기록 병합 (중복 제거)
  const existingQueries = new Set(
    userHistory.map((item) => item.query.trim().toLowerCase())
  );

  const newItems = anonymousHistory.filter(
    (item) => !existingQueries.has(item.query.trim().toLowerCase())
  );

  if (newItems.length > 0) {
    const mergedHistory = [...userHistory, ...newItems]
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, MAX_HISTORY_ITEMS);

    saveSearchHistory(mergedHistory, userId);
  }

  // anonymous 기록 삭제
  clearSearchHistory();
};
