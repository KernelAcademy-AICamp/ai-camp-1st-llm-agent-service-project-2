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
  RAGChatRequest,
  RAGChatResponse,
  AnalyzeRequest,
  AnalyzeResponse,
  HealthResponse,
  AdapterRequest,
  AdapterResponse,
  APIError,
  CasesResponse,
  CaseAnalysis,
  CriminalCaseAnalysis,
  CriminalCaseListItem,
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
  PrecedentListResponse,
  UserDocument,
  UserDocumentDetail,
  UserDocumentsListResponse,
  UploadDocumentResponse,
  UserDocumentType,
  UserDocumentLanguage,
  DocumentChunk,
  Summary,
  KeyClause,
  SummaryResponse,
  ClausesResponse,
  AnalyzeDocumentResponse,
  Organization,
  OrganizationDetail,
  OrganizationsListResponse,
  Membership,
  Project,
  ProjectsListResponse,
  CreateOrganizationRequest,
  UpdateOrganizationRequest,
  AddMemberRequest,
  UpdateMemberRoleRequest,
  CreateProjectRequest,
  UpdateProjectRequest,
  MemberRole,
  RiskAnalysisResponse,
  AnalyzeRiskResponse,
  CaseAnalysisResponse,
  AnalyzeCaseRequest,
  AnalyzeCaseResponse,
  LLMModelConfig,
  LLMModelConfigListItem,
  CompareRequest,
  CompareResponse,
  LLMComparisonHistory,
  EvaluateComparisonRequest,
  LLMUsageStats,
  RiskOverview,
  RiskDocumentsListResponse,
  RiskSeverity,
  SearchHistoryItem,
  RAGFilterOptions,
  RAGSource,
  // Analysis Pipeline Types
  UploadAndAnalyzeResponse,
  AnalysisStatusResponse,
  StartAnalysisResponse,
  // Criminal Analysis Types
  CriminalAnalysisResponse,
  RelatedPrecedentsResponse,
  // Criminal Dashboard Types
  CriminalDashboardSummary,
  SimilarCaseStatisticsResponse,
  CriminalCase,
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
        console.error('API Error Details:', error);
        throw new Error(error.detail || 'API request failed');
      }

      // Handle 204 No Content response (e.g., DELETE requests)
      if (response.status === 204) {
        return {} as T;
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
    return this.fetch<HealthResponse>('/api/v1/ai/health');
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

  /**
   * RAG Chat with Constitutional AI
   * ChromaDB 388K docs + Hybrid Search + Constitutional AI
   */
  async chatWithRAG(request: RAGChatRequest, token?: string): Promise<RAGChatResponse> {
    return this.fetch<RAGChatResponse>('/api/v1/ai/chat/rag', {
      method: 'POST',
      body: JSON.stringify(request),
    }, token);
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

  /**
   * Get full document detail by source ID
   * Retrieves complete text and metadata from VectorDB
   */
  async getDocumentDetail(sourceId: string): Promise<{
    id: string;
    source: string;
    title: string;
    type: string;
    case_number: string;
    date: string;
    citation: string;
    full_text: string;
    metadata: Record<string, any>;
  }> {
    return this.fetch(`/api/document/${encodeURIComponent(sourceId)}`);
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

  async getCases(token?: string): Promise<CasesResponse> {
    return this.fetch<CasesResponse>('/api/v1/cases/', {}, token);
  }

  async getCase(caseId: string): Promise<CaseAnalysis> {
    return this.fetch<CaseAnalysis>(`/api/v1/cases/${caseId}`);
  }

  async uploadCaseFiles(files: File[], token?: string): Promise<CaseAnalysis> {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const url = `${this.baseURL}/api/v1/cases/upload/`;
    const headers: Record<string, string> = {};

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
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

  async deleteCase(caseId: string, token?: string): Promise<DeleteResponse> {
    return this.fetch<DeleteResponse>(`/api/v1/cases/${caseId}/`, {
      method: 'DELETE',
    }, token);
  }

  // ============================================
  // Criminal Case Management (형사 사건 관리)
  // ============================================

  async getCriminalCases(token?: string): Promise<{ cases: CriminalCaseListItem[]; total: number }> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/criminal/cases`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, { headers });

      if (!response.ok) {
        throw new Error('Criminal cases API failed');
      }

      const rawCases = await response.json();
      // API 응답의 'id' 필드를 'case_id'로 매핑
      const cases = (Array.isArray(rawCases) ? rawCases : []).map((c: any) => ({
        case_id: c.id || c.case_id,  // id → case_id 매핑
        case_name: c.case_name,
        summary: c.summary || '',
        document_count: c.document_count || 0,
        crime_type: c.crime_type,
        stage: c.stage,
        next_schedule: c.next_schedule,
        created_at: c.created_at,
        analysis_status: c.analysis_status,
      }));
      return { cases, total: cases.length };
    } catch {
      // Fallback to regular cases API
      try {
        const regularCases = await this.getCases(token);
        return {
          cases: regularCases.cases.map(c => ({
            case_id: c.case_id,
            case_name: c.case_name,
            summary: c.summary,
            document_count: c.document_count,
            created_at: c.created_at,
          })),
          total: regularCases.total,
        };
      } catch {
        // Final fallback: return empty array when all APIs fail
        console.log('All cases APIs failed, returning empty list');
        return { cases: [], total: 0 };
      }
    }
  }

  async getCriminalCase(caseId: string, token?: string): Promise<CriminalCaseAnalysis> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/criminal/cases/${caseId}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, { headers });

      if (!response.ok) {
        throw new Error('Criminal case API failed');
      }

      return await response.json();
    } catch {
      // Fallback to regular case API
      const regularCase = await this.getCase(caseId);
      return regularCase as CriminalCaseAnalysis;
    }
  }

  async uploadCriminalCaseFiles(
    files: File[],
    documentCategory: string,
    token?: string,
    confirmedTexts?: Record<string, string>  // OCR로 추출된 텍스트 (파일명 -> 텍스트)
  ): Promise<CriminalCaseAnalysis> {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    // documentCategory를 crime_type으로 매핑 (API 스키마에 맞춤)
    if (documentCategory && documentCategory !== 'other') {
      formData.append('crime_type', documentCategory);
    }
    // OCR로 추출된 텍스트가 있으면 전달
    if (confirmedTexts && Object.keys(confirmedTexts).length > 0) {
      formData.append('confirmed_texts', JSON.stringify(confirmedTexts));
    }

    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    // analyze-and-save: 분석 + DB 저장 (새로고침해도 유지됨)
    const url = `${AI_SERVICE_URL}/v2/cases/criminal/analyze-and-save`;
    const headers: Record<string, string> = {};

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: response.statusText,
        }));
        throw new Error(error.detail || 'Upload failed');
      }

      const rawResponse = await response.json();
      // API 응답의 'id' 필드를 'case_id'로 매핑
      return {
        ...rawResponse,
        case_id: rawResponse.id || rawResponse.case_id,
      };
    } catch {
      // Fallback to regular upload API
      const regularAnalysis = await this.uploadCaseFiles(files, token);
      return regularAnalysis as CriminalCaseAnalysis;
    }
  }

  async deleteCriminalCase(caseId: string, token?: string): Promise<DeleteResponse> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/criminal/cases/${caseId}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        method: 'DELETE',
        headers,
      });

      if (!response.ok) {
        throw new Error('Criminal case delete API failed');
      }

      return { success: true, message: 'Criminal case deleted successfully' };
    } catch {
      // Fallback to regular delete API
      return await this.deleteCase(caseId, token);
    }
  }

  /**
   * Search precedents for a criminal case asynchronously
   * Called after initial case analysis to search related precedents
   */
  async searchPrecedentsForCase(
    caseId: string,
    token?: string
  ): Promise<{
    success: boolean;
    precedents: Array<{
      case_number: string;
      court: string;
      date: string;
      crime_type: string;
      sentence: string;
      summary: string;
      relevance: number;
    }>;
    precedents_status: string;
    error?: string;
  }> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/cases/criminal/cases/${caseId}/search-precedents`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: response.statusText,
        }));
        return {
          success: false,
          precedents: [],
          precedents_status: 'failed',
          error: error.detail || 'Failed to search precedents',
        };
      }

      return await response.json();
    } catch (error) {
      console.error('searchPrecedentsForCase error:', error);
      return {
        success: false,
        precedents: [],
        precedents_status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // ============================================
  // Criminal Dashboard (형사 사건 현황 대시보드)
  // ============================================

  /**
   * Get criminal cases for dashboard with full details
   * Returns CriminalCase array with schedules and analysis data
   */
  async getCriminalCasesForDashboard(token?: string): Promise<{ cases: CriminalCase[] }> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/criminal/dashboard`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, { headers });

      if (!response.ok) {
        throw new Error('Dashboard API failed');
      }

      return await response.json();
    } catch {
      // Fallback: Convert from regular criminal cases API
      try {
        const listResponse = await this.getCriminalCases(token);
        const cases: CriminalCase[] = (listResponse.cases || []).map(item => ({
          id: item.case_id,
          user_id: '',
          case_name: item.case_name,
          summary: item.summary,
          crime_type: item.crime_type || '',
          crime_elements: { objective: [], subjective: [] },
          sentencing_factors: { favorable: [], unfavorable: [] },
          expected_sentence: { range: '', suspended_probability: 0 },
          defense_strategies: [],
          related_precedents: [],
          stage: item.stage || 'INVESTIGATION',
          schedules: item.next_schedule ? [item.next_schedule] : [],
          conditions: [],
          uploaded_files: [],
          created_at: new Date(item.created_at * 1000).toISOString(),
          updated_at: new Date(item.created_at * 1000).toISOString(),
        }));
        return { cases };
      } catch {
        // Final fallback: return empty cases array when all APIs fail
        console.log('All criminal cases APIs failed, returning empty list');
        return { cases: [] };
      }
    }
  }

  /**
   * Get criminal dashboard summary with aggregated stats
   */
  async getCriminalDashboardSummary(token?: string): Promise<CriminalDashboardSummary> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/criminal/dashboard/summary`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { headers });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Failed to get dashboard summary');
    }

    return response.json();
  }

  /**
   * Get similar case statistics for sentencing prediction
   */
  async getSimilarCaseStatistics(
    crimeType: string,
    conditions: string[] = []
  ): Promise<SimilarCaseStatisticsResponse> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/criminal/statistics/similar-cases`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        crime_type: crimeType,
        conditions,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Failed to get similar case statistics');
    }

    return response.json();
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
    // Backend expects JSON with email and password fields
    const url = `${this.baseURL}/api/v1/auth/login`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: credentials.username, // username field is actually email
        password: credentials.password,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || error.error || 'Login failed');
    }

    const data = await response.json();
    // Backend returns 'access' not 'access_token'
    return {
      access_token: data.access,
      refresh_token: data.refresh,
      user: data.user,
    };
  }

  async signup(data: SignupRequest): Promise<TokenResponse> {
    return this.fetch<TokenResponse>('/api/v1/auth/signup', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async logout(token: string): Promise<SuccessResponse> {
    return this.fetch<SuccessResponse>('/api/v1/auth/logout', {
      method: 'POST',
    }, token);
  }

  async getCurrentUser(token: string): Promise<User> {
    return this.fetch<User>('/api/v1/auth/me', {}, token);
  }

  async updateProfile(data: ProfileUpdateRequest, token: string): Promise<User> {
    return this.fetch<User>('/api/v1/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    }, token);
  }

  async changePassword(data: ChangePasswordRequest, token: string): Promise<SuccessResponse> {
    return this.fetch<SuccessResponse>('/api/v1/auth/change-password', {
      method: 'PUT',
      body: JSON.stringify(data),
    }, token);
  }

  async deactivateAccount(token: string): Promise<SuccessResponse> {
    return this.fetch<SuccessResponse>('/api/v1/auth/account', {
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

  async scrapePrecedentByKeyword(
    keyword: string,
    limit: number = 10
  ): Promise<{ success: boolean; message: string; stored_count: number; fetched_count: number }> {
    return this.fetch<{ success: boolean; message: string; stored_count: number; fetched_count: number }>(
      `/api/precedents/search-keyword`,
      {
        method: 'POST',
        body: JSON.stringify({ keyword, limit }),
      }
    );
  }

  async searchVectorDB(
    keyword: string,
    top_k: number = 20
  ): Promise<{
    success: boolean;
    message: string;
    total_count: number;
    results: Array<{
      case_number: string;
      title: string;
      summary: string;
      court: string;
      decision_date: string;
      score: number;
    }>;
  }> {
    return this.fetch<{
      success: boolean;
      message: string;
      total_count: number;
      results: Array<{
        case_number: string;
        title: string;
        summary: string;
        court: string;
        decision_date: string;
        score: number;
      }>;
    }>(
      `/api/precedents/search-vectordb`,
      {
        method: 'POST',
        body: JSON.stringify({ keyword, top_k }),
      }
    );
  }

  async searchPrecedentsByKeyword(
    keyword: string,
    limit: number = 20,
    offset: number = 0
  ): Promise<PrecedentListResponse> {
    const params = new URLSearchParams({
      keyword,
      limit: limit.toString(),
      offset: offset.toString(),
    });

    return this.fetch<PrecedentListResponse>(
      `/api/precedents/search/keyword?${params}`
    );
  }

  // ============================================
  // Precedent Feedback (판례 피드백)
  // ============================================

  async submitPrecedentFeedback(data: {
    precedent_id: string;
    query: string;
    feedback_type: 'like' | 'dislike';
    is_helpful: boolean;
    relevance_score?: number;
    comment?: string;
    user_id?: string;
    session_id?: string;
  }): Promise<{
    id: string;
    precedent_id: string;
    feedback_type: string;
    is_helpful: boolean;
    created_at: string;
    message: string;
  }> {
    return this.fetch('/api/feedback/submit', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPrecedentFeedbackStats(precedentId: string): Promise<{
    precedent_id: string;
    total_likes: number;
    total_dislikes: number;
    like_ratio: number;
    total_feedback_count: number;
    avg_relevance_score: number | null;
    should_exclude: boolean;
  }> {
    return this.fetch(`/api/feedback/stats/${encodeURIComponent(precedentId)}`);
  }

  // ============================================
  // User Documents (문서 업로드)
  // ============================================

  async uploadDocument(
    file: File,
    title: string,
    docType: UserDocumentType,
    language: UserDocumentLanguage = 'ko',
    token?: string
  ): Promise<UploadDocumentResponse> {
    const formData = new FormData();
    formData.append('original_file', file);
    formData.append('title', title);
    formData.append('doc_type', docType);
    formData.append('language', language);

    const url = `${this.baseURL}/api/v1/documents/upload/`;
    const headers: Record<string, string> = {};

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || error.error || 'Upload failed');
    }

    return await response.json();
  }

  async getUserDocuments(
    token?: string,
    docType?: UserDocumentType,
    status?: string,
    search?: string,
    dateFrom?: string,
    dateTo?: string
  ): Promise<UserDocumentsListResponse> {
    const params = new URLSearchParams();

    if (docType) {
      params.append('doc_type', docType);
    }
    if (status) {
      params.append('status', status);
    }
    if (search) {
      params.append('search', search);
    }
    if (dateFrom) {
      params.append('date_from', dateFrom);
    }
    if (dateTo) {
      params.append('date_to', dateTo);
    }

    const queryString = params.toString();
    const endpoint = `/api/v1/documents/${queryString ? '?' + queryString : ''}`;

    return this.fetch<UserDocumentsListResponse>(endpoint, {}, token);
  }

  async getUserDocumentDetail(documentId: string, token?: string): Promise<UserDocumentDetail> {
    return this.fetch<UserDocumentDetail>(
      `/api/v1/documents/${documentId}/`,
      {},
      token
    );
  }

  async deleteUserDocument(documentId: string, token?: string): Promise<DeleteResponse> {
    return this.fetch<DeleteResponse>(
      `/api/v1/documents/${documentId}/`,
      { method: 'DELETE' },
      token
    );
  }

  async getUserDocumentChunks(documentId: string, token?: string): Promise<{
    document_id: string;
    document_title: string;
    chunk_count: number;
    chunks: DocumentChunk[];
  }> {
    return this.fetch(
      `/api/v1/documents/${documentId}/chunks/`,
      {},
      token
    );
  }

  // ============================================
  // Document Analysis (Summary & Clauses) - Phase 3-2
  // ============================================

  /**
   * Get document summary
   * Returns the latest GLOBAL summary for the document
   */
  async getDocumentSummary(documentId: string, token?: string): Promise<SummaryResponse> {
    return this.fetch<SummaryResponse>(
      `/api/v1/documents/${documentId}/summary/`,
      {},
      token
    );
  }

  /**
   * Get document clauses
   * Returns all extracted key clauses for the document
   */
  async getDocumentClauses(documentId: string, token?: string): Promise<ClausesResponse> {
    return this.fetch<ClausesResponse>(
      `/api/v1/documents/${documentId}/clauses/`,
      {},
      token
    );
  }

  /**
   * Trigger document analysis
   * @param analysisType - 'summary' | 'clauses' | 'both' (default: 'both')
   */
  async analyzeDocument(
    documentId: string,
    token?: string,
    analysisType: 'summary' | 'clauses' | 'both' = 'both'
  ): Promise<AnalyzeDocumentResponse> {
    return this.fetch<AnalyzeDocumentResponse>(
      `/api/v1/documents/${documentId}/analyze/`,
      {
        method: 'POST',
        body: JSON.stringify({ analysis_type: analysisType }),
      },
      token
    );
  }

  /**
   * Extract clauses preview (without saving to DB)
   * Returns extracted clauses for user to select which ones to save
   */
  async extractClausesPreview(documentId: string, token?: string): Promise<{
    success: boolean;
    document_id: string;
    document_title: string;
    clauses: KeyClause[];
    clause_count: number;
  }> {
    return this.fetch(
      `/api/v1/documents/${documentId}/extract_clauses_preview/`,
      { method: 'POST' },
      token
    );
  }

  /**
   * Save selected clauses to database
   * Only saves the clauses user has selected
   */
  async saveSelectedClauses(
    documentId: string,
    clauses: KeyClause[],
    token?: string
  ): Promise<{
    success: boolean;
    document_id: string;
    saved_count: number;
    clauses: KeyClause[];
  }> {
    return this.fetch(
      `/api/v1/documents/${documentId}/save_selected_clauses/`,
      {
        method: 'POST',
        body: JSON.stringify({ clauses }),
      },
      token
    );
  }

  // ============================================
  // Document Analysis with Model Selection
  // ============================================

  /**
   * Generate document summary with specific model
   * @param documentId - Document ID
   * @param modelId - Optional model ID to use
   * @param token - Auth token
   */
  async generateSummaryWithModel(
    documentId: string,
    modelId?: string,
    token?: string
  ): Promise<{
    success: boolean;
    summary: {
      id: string;
      content: string;
      summary_type: string;
      llm_model: string;
      created_at: string;
      meta?: Record<string, any>;
    };
    model_used: string;
    processing_time_ms?: number;
  }> {
    const body: Record<string, any> = { analysis_type: 'summary' };
    if (modelId) {
      body.model_id = modelId;
    }
    return this.fetch(
      `/api/v1/documents/${documentId}/analyze/`,
      {
        method: 'POST',
        body: JSON.stringify(body),
      },
      token
    );
  }

  /**
   * Extract clauses with specific model
   * @param documentId - Document ID
   * @param modelId - Optional model ID to use
   * @param token - Auth token
   */
  async extractClausesWithModel(
    documentId: string,
    modelId?: string,
    token?: string
  ): Promise<{
    success: boolean;
    document_id: string;
    document_title: string;
    clauses: KeyClause[];
    clause_count: number;
    model_used: string;
    processing_time_ms?: number;
  }> {
    const body: Record<string, any> = {};
    if (modelId) {
      body.model_id = modelId;
    }
    return this.fetch(
      `/api/v1/documents/${documentId}/extract_clauses_preview/`,
      {
        method: 'POST',
        body: JSON.stringify(body),
      },
      token
    );
  }

  /**
   * Analyze document risk with specific model
   * @param documentId - Document ID
   * @param modelId - Optional model ID to use
   * @param token - Auth token
   */
  async analyzeRiskWithModel(
    documentId: string,
    modelId?: string,
    token?: string
  ): Promise<AnalyzeRiskResponse & { model_used?: string; processing_time_ms?: number }> {
    const body: Record<string, any> = {};
    if (modelId) {
      body.model_id = modelId;
    }
    return this.fetch<AnalyzeRiskResponse & { model_used?: string; processing_time_ms?: number }>(
      `/api/v1/documents/${documentId}/analyze_risk/`,
      {
        method: 'POST',
        body: JSON.stringify(body),
      },
      token
    );
  }

  // ============================================
  // Risk Analysis - Phase 3-4
  // ============================================

  /**
   * Get document risk analysis
   * Returns the risk analysis result if it exists
   */
  async getDocumentRiskAnalysis(documentId: string, token?: string): Promise<RiskAnalysisResponse> {
    return this.fetch<RiskAnalysisResponse>(
      `/api/v1/documents/${documentId}/risk_analysis/`,
      {},
      token
    );
  }

  /**
   * Analyze document risk
   * Triggers risk analysis for the document
   */
  async analyzeDocumentRisk(documentId: string, token?: string): Promise<AnalyzeRiskResponse> {
    return this.fetch<AnalyzeRiskResponse>(
      `/api/v1/documents/${documentId}/analyze_risk/`,
      { method: 'POST' },
      token
    );
  }

  // ============================================
  // Organizations - Phase 3-3
  // ============================================

  /**
   * Get all organizations for the current user
   */
  async getOrganizations(token?: string): Promise<OrganizationsListResponse> {
    return this.fetch<OrganizationsListResponse>(
      '/api/v1/organizations/',
      {},
      token
    );
  }

  /**
   * Create a new organization
   */
  async createOrganization(
    data: CreateOrganizationRequest,
    token?: string
  ): Promise<Organization> {
    return this.fetch<Organization>(
      '/api/v1/organizations/',
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
      token
    );
  }

  /**
   * Get organization detail with members
   */
  async getOrganization(organizationId: string, token?: string): Promise<OrganizationDetail> {
    return this.fetch<OrganizationDetail>(
      `/api/v1/organizations/${organizationId}/`,
      {},
      token
    );
  }

  /**
   * Update organization
   */
  async updateOrganization(
    organizationId: string,
    data: UpdateOrganizationRequest,
    token?: string
  ): Promise<Organization> {
    return this.fetch<Organization>(
      `/api/v1/organizations/${organizationId}/`,
      {
        method: 'PUT',
        body: JSON.stringify(data),
      },
      token
    );
  }

  /**
   * Delete organization
   */
  async deleteOrganization(organizationId: string, token?: string): Promise<DeleteResponse> {
    return this.fetch<DeleteResponse>(
      `/api/v1/organizations/${organizationId}/`,
      { method: 'DELETE' },
      token
    );
  }

  // ============================================
  // Organization Members - Phase 3-3
  // ============================================

  /**
   * Get organization members
   */
  async getOrganizationMembers(organizationId: string, token?: string): Promise<{
    count: number;
    results: Membership[];
  }> {
    return this.fetch(
      `/api/v1/organizations/${organizationId}/members/`,
      {},
      token
    );
  }

  /**
   * Add member to organization
   */
  async addMember(
    organizationId: string,
    data: AddMemberRequest,
    token?: string
  ): Promise<Membership> {
    return this.fetch<Membership>(
      `/api/v1/organizations/${organizationId}/add_member/`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
      token
    );
  }

  /**
   * Remove member from organization
   */
  async removeMember(
    organizationId: string,
    userId: string,
    token?: string
  ): Promise<SuccessResponse> {
    return this.fetch<SuccessResponse>(
      `/api/v1/organizations/${organizationId}/remove_member/${userId}/`,
      { method: 'DELETE' },
      token
    );
  }

  /**
   * Update member role
   */
  async updateMemberRole(
    organizationId: string,
    userId: string,
    data: UpdateMemberRoleRequest,
    token?: string
  ): Promise<Membership> {
    return this.fetch<Membership>(
      `/api/v1/organizations/${organizationId}/update_member_role/${userId}/`,
      {
        method: 'PUT',
        body: JSON.stringify(data),
      },
      token
    );
  }

  // ============================================
  // Projects - Phase 3-3
  // ============================================

  /**
   * Get all projects (optionally filtered by organization)
   */
  async getProjects(organizationId?: string, token?: string): Promise<ProjectsListResponse> {
    const params = new URLSearchParams();
    if (organizationId) {
      params.append('organization', organizationId);
    }

    const queryString = params.toString();
    const endpoint = `/api/v1/projects/${queryString ? '?' + queryString : ''}`;

    return this.fetch<ProjectsListResponse>(endpoint, {}, token);
  }

  /**
   * Create a new project
   */
  async createProject(data: CreateProjectRequest, token?: string): Promise<Project> {
    return this.fetch<Project>(
      '/api/v1/projects/',
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
      token
    );
  }

  /**
   * Get project detail
   */
  async getProject(projectId: string, token?: string): Promise<Project> {
    return this.fetch<Project>(
      `/api/v1/projects/${projectId}/`,
      {},
      token
    );
  }

  /**
   * Update project
   */
  async updateProject(
    projectId: string,
    data: UpdateProjectRequest,
    token?: string
  ): Promise<Project> {
    return this.fetch<Project>(
      `/api/v1/projects/${projectId}/`,
      {
        method: 'PUT',
        body: JSON.stringify(data),
      },
      token
    );
  }

  /**
   * Delete project
   */
  async deleteProject(projectId: string, token?: string): Promise<DeleteResponse> {
    return this.fetch<DeleteResponse>(
      `/api/v1/projects/${projectId}/`,
      { method: 'DELETE' },
      token
    );
  }

  // ==============================
  // Document Case Analysis Methods
  // ==============================

  /**
   * Get case analysis for a document
   */
  async getCaseAnalysis(documentId: string, token?: string): Promise<CaseAnalysisResponse> {
    return this.fetch<CaseAnalysisResponse>(
      `/api/v1/documents/${documentId}/case-analysis/`,
      {},
      token
    );
  }

  /**
   * Trigger case analysis for a document
   */
  async analyzeCase(
    documentId: string,
    data?: AnalyzeCaseRequest,
    token?: string
  ): Promise<AnalyzeCaseResponse> {
    return this.fetch<AnalyzeCaseResponse>(
      `/api/v1/documents/${documentId}/analyze-case/`,
      {
        method: 'POST',
        body: data ? JSON.stringify(data) : JSON.stringify({}),
      },
      token
    );
  }

  // ============================================
  // LLM Models Management - Phase 3-5
  // ============================================

  /**
   * Get all LLM model configurations
   */
  async getLLMModels(
    params?: { status?: string; provider?: string; active_only?: boolean },
    token?: string
  ): Promise<{ count: number; results: LLMModelConfigListItem[] }> {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status', params.status);
    if (params?.provider) queryParams.append('provider', params.provider);
    if (params?.active_only) queryParams.append('active_only', 'true');

    const queryString = queryParams.toString();
    const endpoint = `/api/v1/llm/models/${queryString ? '?' + queryString : ''}`;

    return this.fetch(endpoint, {}, token);
  }

  /**
   * Get active LLM models only
   */
  async getActiveLLMModels(token?: string): Promise<LLMModelConfigListItem[]> {
    return this.fetch<LLMModelConfigListItem[]>(
      '/api/v1/llm/models/active/',
      {},
      token
    );
  }

  /**
   * Get default LLM model
   */
  async getDefaultLLMModel(token?: string): Promise<LLMModelConfig> {
    return this.fetch<LLMModelConfig>(
      '/api/v1/llm/models/default/',
      {},
      token
    );
  }

  /**
   * Get LLM model detail
   */
  async getLLMModel(modelId: string, token?: string): Promise<LLMModelConfig> {
    return this.fetch<LLMModelConfig>(
      `/api/v1/llm/models/${modelId}/`,
      {},
      token
    );
  }

  // ============================================
  // LLM Comparison - Phase 3-5
  // ============================================

  /**
   * Compare multiple LLM models
   */
  async compareLLMModels(
    request: CompareRequest,
    token?: string
  ): Promise<CompareResponse> {
    return this.fetch<CompareResponse>(
      '/api/v1/llm/compare/compare/',
      {
        method: 'POST',
        body: JSON.stringify(request),
      },
      token
    );
  }

  /**
   * Evaluate comparison result (select preferred model)
   */
  async evaluateComparison(
    request: EvaluateComparisonRequest,
    token?: string
  ): Promise<{ message: string; session_id: string; preferred_model_id: string }> {
    return this.fetch(
      '/api/v1/llm/compare/evaluate/',
      {
        method: 'POST',
        body: JSON.stringify(request),
      },
      token
    );
  }

  /**
   * Get comparison history
   */
  async getComparisonHistory(token?: string): Promise<LLMComparisonHistory[]> {
    return this.fetch<LLMComparisonHistory[]>(
      '/api/v1/llm/compare/history/',
      {},
      token
    );
  }

  // ============================================
  // LLM Usage Stats - Phase 3-5
  // ============================================

  /**
   * Get LLM usage statistics for current user
   */
  async getLLMUsageStats(token?: string): Promise<LLMUsageStats> {
    return this.fetch<LLMUsageStats>(
      '/api/v1/llm/logs/stats/',
      {},
      token
    );
  }

  // ============================================
  // Full Document Retrieval (Qdrant) - v2 API
  // ============================================

  /**
   * Get full document text from Qdrant (all chunks combined)
   * Used for source detail modal to show complete document
   */
  async getFullDocument(
    filterField: string,
    filterValue: string
  ): Promise<{
    full_text: string;
    chunk_count: number;
    metadata: {
      title: string;
      case_number: string;
      court: string;
      date: string;
      doc_type: string;
      source: string;
    };
    timestamp: string;
  }> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/rag/document/full`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        filter_field: filterField,
        filter_value: filterValue,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Failed to fetch full document');
    }

    return response.json();
  }

  // ============================================
  // Risk Dashboard - Phase 3-7
  // ============================================

  /**
   * Get risk overview statistics
   * Returns aggregated risk data for dashboard
   */
  async getRiskOverview(token?: string): Promise<RiskOverview> {
    return this.fetch<RiskOverview>(
      '/api/v1/documents/risk-overview/',
      {},
      token
    );
  }

  /**
   * Get documents with risk analysis
   * Supports filtering, sorting, and pagination
   */
  async getDocumentsWithRisk(
    params?: {
      page?: number;
      page_size?: number;
      severity?: RiskSeverity;
      min_risk_score?: number;
      max_risk_score?: number;
      sort_by?: 'risk_score' | 'created_at' | 'document_title';
      sort_order?: 'asc' | 'desc';
    },
    token?: string
  ): Promise<RiskDocumentsListResponse> {
    const queryParams = new URLSearchParams();

    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
    if (params?.severity) queryParams.append('severity', params.severity);
    if (params?.min_risk_score !== undefined) queryParams.append('min_risk_score', params.min_risk_score.toString());
    if (params?.max_risk_score !== undefined) queryParams.append('max_risk_score', params.max_risk_score.toString());
    if (params?.sort_by) queryParams.append('sort_by', params.sort_by);
    if (params?.sort_order) queryParams.append('sort_order', params.sort_order);

    const queryString = queryParams.toString();
    const endpoint = `/api/v1/documents/with-risk/${queryString ? '?' + queryString : ''}`;

    return this.fetch<RiskDocumentsListResponse>(endpoint, {}, token);
  }

  // ============================================
  // Search History - User Search History API
  // ============================================

  /**
   * Get search history for current user
   * Returns up to 50 most recent search history items
   */
  async getSearchHistory(token: string): Promise<SearchHistoryItem[]> {
    const response = await this.fetch<Array<{
      id: string;
      query: string;
      top_k: number;
      response_mode: 'auto' | 'concise' | 'standard' | 'detailed';
      filters: RAGFilterOptions;
      source_count: number | null;
      answer: string | null;
      sources: RAGSource[] | null;
      model: string | null;
      revised: boolean;
      created_at: string;
    }>>('/api/v1/users/search-history/', {}, token);

    // Transform backend response to frontend SearchHistoryItem format
    // DRF may return array directly or wrap in { results: [...] }
    const items = Array.isArray(response) ? response : (response as { results: typeof response }).results || [];
    return items.map(item => ({
      id: item.id,
      query: item.query,
      timestamp: item.created_at,
      topK: item.top_k,
      responseMode: item.response_mode,
      filters: item.filters,
      sourceCount: item.source_count || undefined,
      answer: item.answer || undefined,
      sources: item.sources || undefined,
      model: item.model || undefined,
      revised: item.revised,
    }));
  }

  /**
   * Save search history item with answer and sources
   */
  async saveSearchHistory(
    data: {
      query: string;
      top_k: number;
      response_mode: 'auto' | 'concise' | 'standard' | 'detailed';
      filters?: RAGFilterOptions;
      source_count?: number;
      answer?: string;
      sources?: RAGSource[];
      model?: string;
      revised?: boolean;
    },
    token: string
  ): Promise<SearchHistoryItem> {
    const response = await this.fetch<{
      id: string;
      query: string;
      top_k: number;
      response_mode: 'auto' | 'concise' | 'standard' | 'detailed';
      filters: RAGFilterOptions;
      source_count: number | null;
      answer: string | null;
      sources: RAGSource[] | null;
      model: string | null;
      revised: boolean;
      created_at: string;
    }>('/api/v1/users/search-history/', {
      method: 'POST',
      body: JSON.stringify(data),
    }, token);

    return {
      id: response.id,
      query: response.query,
      timestamp: response.created_at,
      topK: response.top_k,
      responseMode: response.response_mode,
      filters: response.filters,
      sourceCount: response.source_count || undefined,
      answer: response.answer || undefined,
      sources: response.sources || undefined,
      model: response.model || undefined,
      revised: response.revised,
    };
  }

  /**
   * Delete a search history item
   */
  async deleteSearchHistoryItem(itemId: string, token: string): Promise<void> {
    await this.fetch<void>(
      `/api/v1/users/search-history/${itemId}/`,
      { method: 'DELETE' },
      token
    );
  }

  /**
   * Clear all search history for current user
   */
  async clearSearchHistory(token: string): Promise<{ message: string }> {
    return this.fetch<{ message: string }>(
      '/api/v1/users/search-history/clear/',
      { method: 'DELETE' },
      token
    );
  }

  // ============================================
  // Analysis Pipeline - Auto Analysis Flow
  // ============================================

  /**
   * Upload document and start auto-analysis pipeline
   * Analysis runs sequentially: Summary → Clauses → Risk Analysis
   * Returns immediately with document info; analysis runs in background
   *
   * @param file - File to upload
   * @param title - Document title
   * @param docType - Document type
   * @param language - Document language (default: 'ko')
   * @param token - Auth token
   * @param confirmedText - Pre-extracted text from OCR (optional). If provided, skips preprocessing.
   */
  async uploadAndAnalyze(
    file: File,
    title: string,
    docType: UserDocumentType,
    language: UserDocumentLanguage = 'ko',
    token?: string,
    confirmedText?: string
  ): Promise<UploadAndAnalyzeResponse> {
    const formData = new FormData();
    formData.append('original_file', file);
    formData.append('title', title);
    formData.append('doc_type', docType);
    formData.append('language', language);

    // Add confirmed text if provided (OCR workflow)
    if (confirmedText) {
      formData.append('confirmed_text', confirmedText);
    }

    const url = `${this.baseURL}/api/v1/documents/upload-and-analyze/`;
    const headers: Record<string, string> = {};

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || error.error || 'Upload and analyze failed');
    }

    return await response.json();
  }

  /**
   * Get current analysis status for polling
   * Returns which analyses are completed
   */
  async getAnalysisStatus(documentId: string, token?: string): Promise<AnalysisStatusResponse> {
    return this.fetch<AnalysisStatusResponse>(
      `/api/v1/documents/${documentId}/analysis-status/`,
      {},
      token
    );
  }

  /**
   * Start analysis for an existing preprocessed document
   * Useful for re-analyzing or starting analysis manually
   */
  async startAnalysis(documentId: string, token?: string): Promise<StartAnalysisResponse> {
    return this.fetch<StartAnalysisResponse>(
      `/api/v1/documents/${documentId}/start-analysis/`,
      { method: 'POST' },
      token
    );
  }

  // ============================================
  // Document Extraction with OCR - Two-Phase Upload
  // ============================================

  /**
   * Extract text from document (Phase 1 of two-phase upload)
   * Uses OCR fallback for scanned PDFs
   *
   * @param file - File to extract text from
   * @returns Extraction result with text and metadata
   */
  async extractDocumentText(file: File): Promise<{
    success: boolean;
    text: string;
    extraction_method: string;
    needs_review: boolean;
    confidence: number;
    file_type: string;
    metadata?: {
      page_count?: number;
      char_count?: number;
      avg_confidence?: number;
      preprocessing?: string;
    };
    error?: string;
    timestamp: string;
  }> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${AI_SERVICE_URL}/v2/documents/extract`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Text extraction failed');
    }

    return response.json();
  }

  /**
   * Confirm extracted text and proceed to analysis (Phase 2 of two-phase upload)
   *
   * @param text - User-confirmed/edited text
   * @param fileType - Original file type
   * @param docType - Document type (CONTRACT, STATUTE, etc.)
   * @param documentId - Optional document ID
   * @param sessionId - Optional session ID
   * @returns Analysis result
   */
  async confirmAndAnalyze(
    text: string,
    fileType: string,
    docType: string = 'OTHER',
    documentId?: string,
    sessionId?: string
  ): Promise<{
    success: boolean;
    document_id?: string;
    doc_type: string;
    summary?: {
      summary: string;
      token_count: number;
      model_version: string;
    };
    clauses: Array<{
      clause_type: string;
      title: string;
      content: string;
      importance_score: number;
    }>;
    chunk_count: number;
    completed_tasks: string[];
    processing_time: number;
    session_id?: string;
    error?: string;
    timestamp: string;
    version: string;
  }> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';

    const response = await fetch(`${AI_SERVICE_URL}/v2/documents/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        file_type: fileType,
        doc_type: docType,
        document_id: documentId,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Analysis failed');
    }

    return response.json();
  }

  // ============================================
  // Criminal Document Analysis - Phase 2
  // ============================================

  /**
   * Get criminal analysis for a document
   * Returns crime elements, sentencing factors, judgment summary, etc.
   */
  async getCriminalAnalysis(
    documentId: string,
    token?: string
  ): Promise<CriminalAnalysisResponse> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/documents/${documentId}/criminal-analysis`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { headers });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Failed to get criminal analysis');
    }

    return response.json();
  }

  /**
   * Trigger criminal document analysis
   * Analyzes crime elements, sentencing factors, judgment summary
   */
  async analyzeCriminalDocument(
    documentId: string,
    token?: string
  ): Promise<CriminalAnalysisResponse> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/documents/${documentId}/analyze-criminal`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Failed to analyze criminal document');
    }

    return response.json();
  }

  // ============================================
  // Sentencing Estimation - Phase 3
  // ============================================

  /**
   * Estimate sentencing range based on crime type and factors
   * Returns expected sentence range and suspended probability
   */
  async estimateSentence(request: {
    crime_type: string;
    sentencing_factors: {
      favorable: string[];
      unfavorable: string[];
    };
  }): Promise<{
    range: string;
    suspended_probability: number;
    reasoning?: string;
  }> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/sentencing/estimate`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Failed to estimate sentence');
    }

    return response.json();
  }

  /**
   * Search criminal precedents with filters
   * Returns precedents matching crime type and other criteria
   */
  async searchCriminalPrecedents(
    query: string,
    options?: {
      crime_type?: string;
      court?: string;
      date_from?: string;
      date_to?: string;
      top_k?: number;
    }
  ): Promise<{
    success: boolean;
    total_count: number;
    results: Array<{
      case_number: string;
      court: string;
      date: string;
      crime_type: string;
      sentence: string;
      summary: string;
      relevance: number;
    }>;
  }> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/precedents/search/criminal`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        ...options,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Failed to search criminal precedents');
    }

    return response.json();
  }

  /**
   * Search related precedents for a criminal document
   * Returns similar cases based on crime type and document content
   */
  async searchRelatedPrecedents(
    documentId: string,
    token?: string,
    crimeType?: string
  ): Promise<RelatedPrecedentsResponse> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';

    const params = new URLSearchParams();
    if (crimeType) {
      params.append('crime_type', crimeType);
    }

    const queryString = params.toString();
    const url = `${AI_SERVICE_URL}/v2/documents/${documentId}/related-precedents${queryString ? '?' + queryString : ''}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { headers });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || 'Failed to search related precedents');
    }

    return response.json();
  }

  // ============================================
  // Live Search - 실시간 법령정보센터 API
  // ============================================

  /**
   * Search live precedents from 국가법령정보센터 API
   * Real-time search (not indexed documents)
   */
  async searchLivePrecedents(params: {
    keyword?: string;
    case_number?: string;
    court?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    display?: number;
    fetch_content?: boolean;
  }): Promise<{
    success: boolean;
    total_count: number;
    precedents: Array<{
      prec_id: string;
      case_number: string;
      case_name: string;
      court: string;
      decision_date: string;
      case_type: string;
      judgment_type: string;
      content: string;
      source_url?: string;
    }>;
    error?: string;
    metadata: Record<string, any>;
    timestamp: string;
  }> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/rag/live/precedents`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        keyword: params.keyword,
        case_number: params.case_number,
        court: params.court,
        start_date: params.start_date,
        end_date: params.end_date,
        page: params.page || 1,
        display: params.display || 20,
        fetch_content: params.fetch_content ?? true,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      return {
        success: false,
        total_count: 0,
        precedents: [],
        error: error.detail || 'Failed to search live precedents',
        metadata: {},
        timestamp: new Date().toISOString(),
      };
    }

    return response.json();
  }

  /**
   * Search live statutes from 국가법령정보센터 API
   * Real-time search (not indexed documents)
   */
  async searchLiveStatutes(params: {
    keyword?: string;
    law_code?: string;
    law_type?: string;
    ministry?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    display?: number;
    fetch_content?: boolean;
  }): Promise<{
    success: boolean;
    total_count: number;
    statutes: Array<{
      law_id: string;
      law_mst: string;
      law_name: string;
      law_type: string;
      ministry: string;
      promulgation_date: string;
      enforcement_date: string;
      content: string;
      source_url?: string;
    }>;
    error?: string;
    metadata: Record<string, any>;
    timestamp: string;
  }> {
    const AI_SERVICE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
    const url = `${AI_SERVICE_URL}/v2/rag/live/statutes`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        keyword: params.keyword,
        law_code: params.law_code,
        law_type: params.law_type,
        ministry: params.ministry,
        start_date: params.start_date,
        end_date: params.end_date,
        page: params.page || 1,
        display: params.display || 20,
        fetch_content: params.fetch_content ?? false,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      return {
        success: false,
        total_count: 0,
        statutes: [],
        error: error.detail || 'Failed to search live statutes',
        metadata: {},
        timestamp: new Date().toISOString(),
      };
    }

    return response.json();
  }
}

// Singleton instance
export const apiClient = new APIClient();

export default apiClient;
