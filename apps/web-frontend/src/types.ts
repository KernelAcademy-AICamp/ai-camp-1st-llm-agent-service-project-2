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

export interface RAGChatRequest {
  query: string;
  top_k?: number;
  include_sources?: boolean;
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
