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
