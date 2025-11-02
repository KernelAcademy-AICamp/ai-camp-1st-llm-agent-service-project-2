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
  case_id: string;
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
