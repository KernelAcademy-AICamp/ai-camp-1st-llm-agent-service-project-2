/**
 * Agent Hub - Theme Hook
 * 다크모드/라이트모드 토글을 관리합니다.
 */

import { useState, useEffect, useCallback } from 'react';
import { storage } from '../lib/utils';

type Theme = 'light' | 'dark';

const THEME_STORAGE_KEY = 'agent-hub-theme';

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    // 초기값: localStorage 또는 시스템 설정
    if (typeof window === 'undefined') return 'light';

    const savedTheme = storage.get<Theme | null>(THEME_STORAGE_KEY, null);
    if (savedTheme) return savedTheme;

    // 시스템 다크모드 감지
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  });

  // 테마 변경 시 DOM 업데이트
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    storage.set(THEME_STORAGE_KEY, theme);

    // 애니메이션 클래스 추가
    root.classList.add('ah-theme-transition');
    const timeout = setTimeout(() => {
      root.classList.remove('ah-theme-transition');
    }, 300);

    return () => clearTimeout(timeout);
  }, [theme]);

  // 시스템 테마 변경 감지
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      // localStorage에 저장된 값이 없을 때만 시스템 설정 따름
      const savedTheme = storage.get<Theme | null>(THEME_STORAGE_KEY, null);
      if (!savedTheme) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  const setLightTheme = useCallback(() => setTheme('light'), []);
  const setDarkTheme = useCallback(() => setTheme('dark'), []);

  return {
    theme,
    isDark: theme === 'dark',
    isLight: theme === 'light',
    toggleTheme,
    setLightTheme,
    setDarkTheme,
  };
}

export default useTheme;
