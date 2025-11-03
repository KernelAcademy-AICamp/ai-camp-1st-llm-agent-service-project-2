/**
 * Authentication Context
 * 앱 전체의 인증 상태를 관리합니다.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, AuthState, LoginRequest, SignupRequest, ProfileUpdateRequest } from '../types';
import apiClient from '../api/client';

interface AuthContextType extends AuthState {
  login: (credentials: LoginRequest) => Promise<void>;
  signup: (data: SignupRequest) => Promise<void>;
  logout: () => void;
  updateProfile: (data: ProfileUpdateRequest) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'lawlaw_auth_token';

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // 초기 로드 시 localStorage에서 토큰 확인 및 자동 로그인
  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem(TOKEN_KEY);

      if (savedToken) {
        try {
          // 토큰으로 사용자 정보 가져오기
          const user = await apiClient.getCurrentUser(savedToken);
          setAuthState({
            user,
            token: savedToken,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          // 토큰이 유효하지 않으면 제거
          console.error('Token validation failed:', error);
          localStorage.removeItem(TOKEN_KEY);
          setAuthState({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          });
        }
      } else {
        setAuthState(prev => ({ ...prev, isLoading: false }));
      }
    };

    initAuth();
  }, []);

  const login = async (credentials: LoginRequest) => {
    try {
      const response = await apiClient.login(credentials);

      // 토큰 저장
      localStorage.setItem(TOKEN_KEY, response.access_token);

      setAuthState({
        user: response.user,
        token: response.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const signup = async (data: SignupRequest) => {
    try {
      const response = await apiClient.signup(data);

      // 토큰 저장
      localStorage.setItem(TOKEN_KEY, response.access_token);

      setAuthState({
        user: response.user,
        token: response.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      console.error('Signup failed:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      if (authState.token) {
        await apiClient.logout(authState.token);
      }
    } catch (error) {
      console.error('Logout API call failed:', error);
    } finally {
      // 클라이언트 측 로그아웃 (API 호출 실패해도 진행)
      localStorage.removeItem(TOKEN_KEY);
      setAuthState({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  };

  const updateProfile = async (data: ProfileUpdateRequest) => {
    if (!authState.token) {
      throw new Error('Not authenticated');
    }

    try {
      const updatedUser = await apiClient.updateProfile(data, authState.token);
      setAuthState(prev => ({
        ...prev,
        user: updatedUser,
      }));
    } catch (error) {
      console.error('Profile update failed:', error);
      throw error;
    }
  };

  const refreshUser = async () => {
    if (!authState.token) {
      throw new Error('Not authenticated');
    }

    try {
      const user = await apiClient.getCurrentUser(authState.token);
      setAuthState(prev => ({
        ...prev,
        user,
      }));
    } catch (error) {
      console.error('User refresh failed:', error);
      throw error;
    }
  };

  const value: AuthContextType = {
    ...authState,
    login,
    signup,
    logout,
    updateProfile,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
