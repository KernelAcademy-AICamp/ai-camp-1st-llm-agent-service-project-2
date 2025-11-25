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
  AnalyzeRiskResponse
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
    search?: string
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
   * Generates both summary and clauses for the document
   */
  async analyzeDocument(documentId: string, token?: string): Promise<AnalyzeDocumentResponse> {
    return this.fetch<AnalyzeDocumentResponse>(
      `/api/v1/documents/${documentId}/analyze/`,
      { method: 'POST' },
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
}

// Singleton instance
export const apiClient = new APIClient();

export default apiClient;
