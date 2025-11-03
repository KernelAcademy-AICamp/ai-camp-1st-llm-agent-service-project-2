/**
 * LawLaw Backend API Client
 *
 * Backend FastAPI 서버와 통신하는 클라이언트 모듈
 */

import {
  SearchRequest,
  SearchResult,
  ChatRequest,
  ChatResponse,
  AnalyzeRequest,
  AnalyzeResponse,
  HealthResponse,
  AdapterRequest,
  AdapterResponse,
  APIError,
  CasesResponse,
  CaseAnalysis,
  DeleteResponse,
  DocumentGenerationRequest,
  DocumentDetail,
  DocumentsResponse,
  ScenariosResponse,
  LoginRequest,
  SignupRequest,
  TokenResponse,
  User,
  ProfileUpdateRequest,
  ChangePasswordRequest,
  SuccessResponse,
  Precedent,
  PrecedentDetail,
  PrecedentListResponse
} from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  /**
   * Generic fetch wrapper with error handling and auth token
   */
  private async fetch<T>(
    endpoint: string,
    options: RequestInit = {},
    token?: string
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Merge existing headers
    if (options.headers) {
      Object.assign(headers, options.headers);
    }

    // Add Authorization header if token is provided
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const error: APIError = await response.json().catch(() => ({
          detail: response.statusText,
          status_code: response.status,
        }));
        throw new Error(error.detail || 'API request failed');
      }

      return await response.json();
    } catch (error) {
      console.error(`API Error (${endpoint}):`, error);
      throw error;
    }
  }

  // ============================================
  // Health Check
  // ============================================

  async healthCheck(): Promise<HealthResponse> {
    return this.fetch<HealthResponse>('/health');
  }

  // ============================================
  // Search
  // ============================================

  async search(request: SearchRequest): Promise<SearchResult[]> {
    return this.fetch<SearchResult[]>('/api/search', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // ============================================
  // Chat
  // ============================================

  async chat(request: ChatRequest): Promise<ChatResponse> {
    return this.fetch<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // ============================================
  // Document Analysis
  // ============================================

  async analyze(request: AnalyzeRequest): Promise<AnalyzeResponse> {
    return this.fetch<AnalyzeResponse>('/api/analyze', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // ============================================
  // Adapter Management (QDoRA)
  // ============================================

  async loadAdapter(adapterName: string): Promise<AdapterResponse> {
    const request: AdapterRequest = { adapter_name: adapterName };
    return this.fetch<AdapterResponse>('/api/adapter/load', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async unloadAdapter(): Promise<AdapterResponse> {
    return this.fetch<AdapterResponse>('/api/adapter/unload', {
      method: 'POST',
    });
  }

  async listAdapters(): Promise<string[]> {
    return this.fetch<string[]>('/api/adapter/list');
  }

  async getAdapterInfo(): Promise<any> {
    return this.fetch<any>('/api/adapter/info');
  }

  // ============================================
  // Case Management
  // ============================================

  async getCases(): Promise<CasesResponse> {
    return this.fetch<CasesResponse>('/api/cases');
  }

  async getCase(caseId: string): Promise<CaseAnalysis> {
    return this.fetch<CaseAnalysis>(`/api/cases/${caseId}`);
  }

  async uploadCaseFiles(files: File[]): Promise<CaseAnalysis> {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const url = `${this.baseURL}/api/cases/upload`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Upload failed');
    }

    return await response.json();
  }

  async deleteCase(caseId: string): Promise<DeleteResponse> {
    return this.fetch<DeleteResponse>(`/api/cases/${caseId}`, {
      method: 'DELETE',
    });
  }

  // ============================================
  // Document Generation
  // ============================================

  async generateDocument(request: DocumentGenerationRequest): Promise<DocumentDetail> {
    return this.fetch<DocumentDetail>('/api/documents/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getDocument(caseId: string, documentId: string): Promise<DocumentDetail> {
    return this.fetch<DocumentDetail>(`/api/documents/${caseId}/${documentId}`);
  }

  async listDocuments(caseId: string): Promise<DocumentsResponse> {
    return this.fetch<DocumentsResponse>(`/api/documents/${caseId}`);
  }

  async deleteDocument(caseId: string, documentId: string): Promise<DeleteResponse> {
    return this.fetch<DeleteResponse>(`/api/documents/${caseId}/${documentId}`, {
      method: 'DELETE',
    });
  }

  async getScenarios(): Promise<ScenariosResponse> {
    return this.fetch<ScenariosResponse>('/api/documents/scenarios');
  }

  // ============================================
  // Authentication
  // ============================================

  async login(credentials: LoginRequest): Promise<TokenResponse> {
    // OAuth2 expects form data, not JSON
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const url = `${this.baseURL}/api/auth/login`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Login failed');
    }

    return await response.json();
  }

  async signup(data: SignupRequest): Promise<TokenResponse> {
    return this.fetch<TokenResponse>('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async logout(token: string): Promise<SuccessResponse> {
    return this.fetch<SuccessResponse>('/api/auth/logout', {
      method: 'POST',
    }, token);
  }

  async getCurrentUser(token: string): Promise<User> {
    return this.fetch<User>('/api/auth/me', {}, token);
  }

  async updateProfile(data: ProfileUpdateRequest, token: string): Promise<User> {
    return this.fetch<User>('/api/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    }, token);
  }

  async changePassword(data: ChangePasswordRequest, token: string): Promise<SuccessResponse> {
    return this.fetch<SuccessResponse>('/api/auth/change-password', {
      method: 'PUT',
      body: JSON.stringify(data),
    }, token);
  }

  async deactivateAccount(token: string): Promise<SuccessResponse> {
    return this.fetch<SuccessResponse>('/api/auth/account', {
      method: 'DELETE',
    }, token);
  }

  // ============================================
  // Precedents (판례)
  // ============================================

  async getRecentPrecedents(
    limit: number = 10,
    offset: number = 0,
    caseType?: string
  ): Promise<PrecedentListResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });

    if (caseType) {
      params.append('case_type', caseType);
    }

    return this.fetch<PrecedentListResponse>(`/api/precedents/recent?${params}`);
  }

  async getPrecedentDetail(precedentId: string): Promise<PrecedentDetail> {
    return this.fetch<PrecedentDetail>(`/api/precedents/${precedentId}`);
  }

  async searchPrecedentsBySpecialization(
    specialization: string,
    limit: number = 20,
    offset: number = 0
  ): Promise<PrecedentListResponse> {
    const params = new URLSearchParams({
      specialization,
      limit: limit.toString(),
      offset: offset.toString(),
    });

    return this.fetch<PrecedentListResponse>(
      `/api/precedents/search/by-specialization?${params}`
    );
  }

  async refreshPrecedents(limit: number = 10): Promise<{ message: string; stored_count: number }> {
    const params = new URLSearchParams({
      limit: limit.toString(),
    });

    return this.fetch<{ message: string; stored_count: number }>(
      `/api/precedents/refresh?${params}`,
      { method: 'POST' }
    );
  }
}

// Singleton instance
export const apiClient = new APIClient();

export default apiClient;
