/**
 * LawLaw 공통 타입 정의
 *
 * Frontend와 Backend에서 공유하는 타입들을 정의합니다.
 * 타입 불일치를 방지하고 코드 일관성을 유지합니다.
 */

// ============================================
// Search Related Types
// ============================================

export type DocumentType = 'case' | 'law' | 'interpretation' | 'decision';

export interface SearchResult {
  id: string;
  title: string;
  type: DocumentType;
  summary: string;
  date: string;
  relevance: number;
  citation?: string;
}

export interface SearchRequest {
  query: string;
  filters?: {
    types?: DocumentType[];
    dateFrom?: string;
    dateTo?: string;
    court?: string;
  };
  limit?: number;
}

// ============================================
// Chat Related Types
// ============================================

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  message: string;
  context?: string;
  temperature?: number;
}

export interface ChatResponse {
  response: string;
  timestamp: string;
  model: string;
  sources?: SourceDocument[];
}

export interface SourceDocument {
  text: string;
  metadata: {
    source?: string;
    title?: string;
    date?: string;
    type?: DocumentType;
    citation?: string;
  };
  score?: number;
}

// ============================================
// RAG Chat Types
// ============================================

export interface RAGFilterOptions {
  doc_types?: UserDocumentType[];
  statuses?: UserDocumentStatus[];
  date_from?: string;  // ISO date string (YYYY-MM-DD)
  date_to?: string;    // ISO date string (YYYY-MM-DD)
  keyword?: string;    // title search only
  document_ids?: string[];  // pre-filtered document IDs (from Django)
}

export type ResponseMode = 'concise' | 'standard' | 'detailed';

export interface RAGChatRequest {
  query: string;
  top_k?: number;
  include_sources?: boolean;
  enable_critique?: boolean;
  response_mode?: ResponseMode;  // Phase 2: 응답 모드 (미지정시 자동 분류)
  filters?: RAGFilterOptions;
}

export interface RAGSource {
  rank?: number;
  source: string;
  content: string;
  type?: string;
  title?: string;
  case_number?: string;
  date?: string;
  citation?: string;
  text_snippet?: string;
  score: number;
  metadata?: {
    doc_id?: string;
    type?: string;
    file?: string;
    source?: string;
    [key: string]: any;
  };
}

export interface RAGChatResponse {
  answer: string;
  sources: RAGSource[];
  query: string;
  model: string;
  timestamp: string;
  revised: boolean;
  response_mode?: ResponseMode;  // Phase 2: 사용된 응답 모드
  auto_classified?: boolean;     // Phase 2: 자동 분류 여부
}

// ============================================
// Document Analysis Types
// ============================================

export interface AnalyzeRequest {
  content: string;
  document_type?: string;
}

export interface AnalyzeResponse {
  analysis: string;
  sources: SourceDocument[];
  timestamp: string;
}

// ============================================
// Adapter Related Types (QDoRA)
// ============================================

export interface AdapterInfo {
  name: string;
  displayName: string;
  description: string;
  specialty: string[];
  size: string; // 예: "150MB"
  version: string;
  accuracy?: number; // 정확도 (0-100%)
}

export interface AdapterRequest {
  adapter_name: string;
}

export interface AdapterResponse {
  success: boolean;
  current_adapter: string | null;
  available_adapters: string[];
  message?: string;
}

// ============================================
// Health Check Types
// ============================================

export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  model_status: 'available' | 'not_found' | 'error';
  timestamp: string;
  current_model?: string;
  adapter_loaded?: boolean;
}

// ============================================
// Error Types
// ============================================

export interface APIError {
  detail: string;
  status_code: number;
  timestamp?: string;
}

// ============================================
// Case Management Types
// ============================================

export interface CaseFile {
  filename: string;
  size: number;
  path?: string;
}

export interface RelatedCase {
  title: string;
  summary: string;
  date: string;
  relevance: number;
}

export interface ScenarioInfo {
  scenario_name: string;
  description: string;
  confidence: number;
  templates: string[];
}

export interface CaseAnalysis {
  case_id: string;
  summary: string;
  document_types: string[];
  issues: string[];
  key_dates: Record<string, string>;
  parties: Record<string, string>;
  related_cases: RelatedCase[];
  suggested_case_name: string;
  suggested_next_steps: string[];
  uploaded_files: CaseFile[];
  scenario?: ScenarioInfo;
}

export interface CaseListItem {
  case_id: string;
  case_name: string;
  summary: string;
  document_count: number;
  created_at: number;
}

export interface CasesResponse {
  cases: CaseListItem[];
  total: number;
}

// ============================================
// Document Generation Types
// ============================================

export type GenerationMode = 'quick' | 'custom';

export interface DocumentGenerationRequest {
  case_id?: string;  // Optional for standalone document generation
  template_name: string;
  generation_mode?: GenerationMode;
  custom_fields?: Record<string, string>;
  user_instructions?: string;
}

export interface DocumentMetadata {
  generated_at: string;
  template_version?: string;
  ai_model?: string;
  generation_mode?: GenerationMode;
  [key: string]: any;
}

export interface GeneratedDocument {
  document_id: string;
  title: string;
  template_used: string;
  created_at: string;
}

export interface DocumentDetail {
  document_id: string;
  title: string;
  content: string;
  template_used: string;
  created_at: string;
  metadata: DocumentMetadata;
}

export interface DocumentsResponse {
  documents: GeneratedDocument[];
  total: number;
}

export interface Scenario {
  name: string;
  description: string;
  templates: string[];
}

export interface ScenariosResponse {
  scenarios: Record<string, Scenario>;
}

export interface TemplateField {
  name: string;
  label: string;
  type: 'text' | 'number' | 'textarea' | 'date';
  placeholder: string;
  required: boolean;
}

// ============================================
// User Preferences (Frontend only, but type-safe)
// ============================================

export interface UserPreferences {
  theme: 'light' | 'dark';
  selectedAdapter?: string;
  dataSources: {
    cases: boolean;
    laws: boolean;
    interpretations: boolean;
    decisions: boolean;
  };
  fontSize: 'small' | 'medium' | 'large';
}

// ============================================
// Common API Response Types
// ============================================

export interface SuccessResponse {
  success: boolean;
  message: string;
}

export interface DeleteResponse extends SuccessResponse {
  // Inherits success and message
}

// ============================================
// Authentication Types
// ============================================

export interface User {
  id: string;
  email: string;
  full_name: string;
  specializations: string[];
  lawyer_registration_number?: string;
  is_active: boolean;
  is_staff: boolean;  // Admin user flag
}

export interface LoginRequest {
  username: string; // OAuth2 standard uses 'username' for email
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  password_confirm: string;
  full_name: string;
  specializations?: string[];
  lawyer_registration_number?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
  user: User;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ProfileUpdateRequest {
  full_name?: string;
  specializations?: string[];
  lawyer_registration_number?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// ============================================
// Precedent Types (판례)
// ============================================

export interface Precedent {
  id: string;
  case_number: string;
  title: string;
  summary: string | null;
  court: string;
  decision_date: string;
  case_type: string;
  specialization_tags: string[];
  case_link: string | null;
  created_at: string;
}

export interface PrecedentDetail extends Precedent {
  full_text: string | null;
  citation: string | null;
  updated_at: string;
}

export interface PrecedentListResponse {
  total: number;
  precedents: Precedent[];
}

// ============================================
// User Document Upload Types
// ============================================

export type UserDocumentType = 'CASE' | 'CONTRACT' | 'STATUTE' | 'PRECEDENT' | 'OTHER';
export type UserDocumentStatus = 'UPLOADED' | 'OCR_DONE' | 'PREPROCESSED' | 'EMBEDDED' | 'FAILED';
export type UserDocumentLanguage = 'ko' | 'en';

export interface UserDocument {
  id: string;
  user: string;
  user_email?: string;
  title: string;
  doc_type: UserDocumentType;
  source_type: string;
  original_file: string | null;
  language: UserDocumentLanguage;
  status: UserDocumentStatus;
  file_size: number | null;
  file_type: string | null;
  page_count: number | null;
  error_message: string | null;
  chunk_count: number;
  is_processing_complete: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunk {
  id: string;
  document: string;
  chunk_index: number;
  text: string;
  start_offset: number | null;
  end_offset: number | null;
  page_number: number | null;
  embedding_id: string | null;
  token_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface UserDocumentDetail extends UserDocument {
  chunks: DocumentChunk[];
  case_analysis?: DocumentCaseAnalysis;  // Case analysis if doc_type is 'CASE'
}

export interface UserDocumentsListResponse {
  count: number;
  results: UserDocument[];
}

export interface UploadDocumentRequest {
  title: string;
  doc_type: UserDocumentType;
  language?: UserDocumentLanguage;
  original_file: File;
}

export interface UploadDocumentResponse {
  message: string;
  document: UserDocument;
}

// ============================================
// Summary and Clause Types (Phase 3-2)
// ============================================

export type SummaryType = 'GLOBAL' | 'SECTION';

export interface Summary {
  id: string;
  document: string;
  llm_model: string;
  summary_type: SummaryType;
  content: string;
  meta: Record<string, any>;
  created_at: string;
}

export type ClauseType =
  | 'PAYMENT'
  | 'OBLIGATION'
  | 'TERMINATION'
  | 'LIABILITY'
  | 'WARRANTY'
  | 'CONFIDENTIALITY'
  | 'DISPUTE'
  | 'IP'
  | 'DELIVERY'
  | 'OTHER';

export interface KeyClause {
  id: string;
  document: string;
  clause_type: ClauseType;
  title: string;
  content: string;
  importance_score: number;
  llm_model: string;
  created_at: string;
}

export interface SummaryResponse {
  summary: Summary | null;
}

export interface ClausesResponse {
  clauses: KeyClause[];
  total: number;
}

export interface AnalyzeDocumentRequest {
  document_id: string;
}

export interface AnalyzeDocumentResponse {
  message: string;
  summary: Summary;
  clauses: KeyClause[];
}

// ============================================
// Organization and Project Types (Phase 3-3)
// ============================================

export type MemberRole = 'ADMIN' | 'EDITOR' | 'VIEWER';

export interface Organization {
  id: string;
  name: string;
  created_by: string;
  settings: Record<string, any>;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface Membership {
  id: string;
  organization: string;
  user: string;
  user_email: string;
  role: MemberRole;
  role_display: string;
  is_admin: boolean;
  can_edit: boolean;
  joined_at: string;
}

export interface Project {
  id: string;
  organization: string;
  organization_name: string;
  name: string;
  description: string;
  created_by: string;
  document_count: number;
  case_count: number;
  created_at: string;
  updated_at: string;
}

export interface OrganizationDetail extends Organization {
  members: Membership[];
}

export interface OrganizationsListResponse {
  count: number;
  results: Organization[];
}

export interface ProjectsListResponse {
  count: number;
  results: Project[];
}

export interface CreateOrganizationRequest {
  name: string;
  settings?: Record<string, any>;
}

export interface UpdateOrganizationRequest {
  name?: string;
  settings?: Record<string, any>;
}

export interface AddMemberRequest {
  user_email: string;
  role: MemberRole;
}

export interface UpdateMemberRoleRequest {
  role: MemberRole;
}

export interface CreateProjectRequest {
  organization: string;
  name: string;
  description?: string;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
}

// ============================================
// Risk Analysis Types (Phase 3-4)
// ============================================

export type RiskSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
export type RiskCategory = 'LEGAL' | 'FINANCIAL' | 'COMPLIANCE' | 'OPERATIONAL' | 'REPUTATIONAL' | 'OTHER';

export interface RiskItem {
  category: RiskCategory;
  title: string;
  description: string;
  severity: RiskSeverity;
  score: number;
  clause_reference: string;
}

export interface RiskAnalysis {
  id: string;
  document: string;
  document_title?: string;
  overall_risk_score: number;
  severity: RiskSeverity;
  severity_display?: string;
  risk_items: RiskItem[];
  recommendations: string[];
  summary: string;
  llm_model: string;
  meta?: Record<string, any>;
  risk_item_count?: number;
  is_high_risk?: boolean;
  created_at: string;
  updated_at?: string;
}

export interface RiskAnalysisResponse {
  document_id: string;
  document_title: string;
  risk_analysis: RiskAnalysis | null;
  message?: string;
}

export interface AnalyzeRiskResponse {
  success: boolean;
  document_id: string;
  document_title: string;
  risk_analysis?: RiskAnalysis;
  error?: string;
}

// ============================================
// Document Case Analysis Types (Document-Case Integration)
// ============================================

export interface DocumentCaseAnalysis {
  id: string;
  document: string;
  document_title?: string;
  suggested_case_name: string;
  document_types: string[];
  parties: Record<string, any>;
  party_count?: number;
  key_dates: Record<string, string>;
  issues: string[];
  issue_count?: number;
  related_precedents: string[];
  has_precedents?: boolean;
  suggested_next_steps: string[];
  scenario?: string;
  llm_model: string;
  created_at: string;
  updated_at?: string;
}

export interface CaseAnalysisResponse {
  document_id: string;
  document_title: string;
  case_analysis: DocumentCaseAnalysis | null;
  message?: string;
}

export interface AnalyzeCaseRequest {
  llm_model?: string;
  scenario?: '소송 준비' | '계약 검토' | '법적 자문' | '기타';
}

export interface AnalyzeCaseResponse {
  success: boolean;
  document_id: string;
  document_title: string;
  case_analysis?: DocumentCaseAnalysis;
  error?: string;
}

// ============================================
// LLM Comparison Types (Phase 3-5)
// ============================================

export type LLMProvider = 'openai' | 'anthropic' | 'google' | 'ollama';
export type LLMModelStatus = 'active' | 'inactive' | 'deprecated';
export type CompareTaskType = 'summarize' | 'clauses' | 'risk_analysis' | 'case_analysis' | 'chat' | 'other';

export interface LLMModelConfig {
  id: string;
  name: string;
  provider: LLMProvider;
  model_id: string;
  api_key_env_var: string;
  base_url: string | null;
  default_temperature: number;
  default_max_tokens: number;
  input_cost_per_1k: string;
  output_cost_per_1k: string;
  status: LLMModelStatus;
  is_default: boolean;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface LLMModelConfigListItem {
  id: string;
  name: string;
  provider: LLMProvider;
  model_id: string;
  status: LLMModelStatus;
  is_default: boolean;
  input_cost_per_1k: string;
  output_cost_per_1k: string;
}

export interface ModelComparisonResult {
  model_id: string;
  model_name: string;
  provider: string;
  status: 'success' | 'error';
  response_text: string | null;
  prompt_tokens: number;
  response_tokens: number;
  total_tokens: number;
  latency_ms: number;
  estimated_cost: number;
  error_message: string | null;
}

export interface CompareRequest {
  text: string;
  task_type: CompareTaskType;
  model_ids?: string[];
  document_id?: string;
  options?: Record<string, any>;
}

export interface CompareResponse {
  session_id: string;
  task_type: string;
  input_text: string;
  results: ModelComparisonResult[];
  total_models: number;
  fastest_model: string | null;
  cheapest_model: string | null;
  summary: Record<string, any>;
}

export interface LLMCallLog {
  id: string;
  user: string;
  model_config: string;
  model_config_name?: string;
  task_type: string;
  prompt_text: string;
  prompt_tokens: number;
  response_text: string;
  response_tokens: number;
  total_tokens: number;
  latency_ms: number;
  status: string;
  error_message: string | null;
  estimated_cost: string;
  comparison_session_id: string | null;
  document_id: string | null;
  meta: Record<string, any>;
  created_at: string;
}

export interface LLMComparisonHistory {
  id: string;
  session_id: string;
  user: string;
  task_type: string;
  input_text: string;
  results: ModelComparisonResult[];
  total_models: number;
  fastest_model: string;
  cheapest_model: string;
  preferred_model_id: string | null;
  evaluation_notes: string | null;
  created_at: string;
}

export interface EvaluateComparisonRequest {
  session_id: string;
  preferred_model_id: string;
  evaluation_notes?: string;
}

export interface LLMUsageStats {
  summary: {
    total_calls: number;
    total_tokens: number;
    total_cost: string | null;
    avg_latency: number | null;
  };
  by_task_type: Array<{
    task_type: string;
    count: number;
    total_tokens: number;
    avg_latency: number;
  }>;
  by_model: Array<{
    model_config__name: string;
    count: number;
    total_tokens: number;
    avg_latency: number;
  }>;
}

// ============================================
// Risk Analysis Dashboard Types (Phase 3-7)
// ============================================

export interface SeverityDistribution {
  CRITICAL: number;
  HIGH: number;
  MEDIUM: number;
  LOW: number;
  INFO: number;
}

export interface CategoryDistribution {
  LEGAL: number;
  FINANCIAL: number;
  COMPLIANCE: number;
  OPERATIONAL: number;
  REPUTATIONAL: number;
  OTHER: number;
}

export interface RecentRiskAnalysis {
  id: string;
  document_id: string;
  document_title: string;
  overall_risk_score: number;
  severity: RiskSeverity;
  risk_item_count: number;
  created_at: string;
}

export interface RiskOverview {
  total_documents: number;
  documents_with_risk: number;
  documents_without_risk: number;
  avg_risk_score: number;
  high_risk_count: number;
  severity_distribution: SeverityDistribution;
  category_distribution: CategoryDistribution;
  recent_analyses: RecentRiskAnalysis[];
}

export interface RiskDocumentListItem {
  document: UserDocument;
  risk_analysis: {
    id: string;
    overall_risk_score: number;
    severity: RiskSeverity;
    risk_item_count: number;
    summary: string;
    llm_model: string;
    created_at: string;
  };
}

export interface RiskDocumentsListResponse {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: RiskDocumentListItem[];
}
