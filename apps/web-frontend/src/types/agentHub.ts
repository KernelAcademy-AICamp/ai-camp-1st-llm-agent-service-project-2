/**
 * Agent Hub - Type Definitions
 */

/**
 * 메시지 역할
 */
export type MessageRole = 'user' | 'assistant' | 'system';

/**
 * 메시지 메타데이터
 */
export interface DocumentClause {
  clause_number?: string;
  clause_type?: string;
  text?: string;
  importance?: string;
  importance_score?: number;
  category?: string;
}

export interface DocumentRisk {
  name?: string;
  description?: string;
  severity?: string;
  level?: string;
  recommendation?: string;
  category?: string;
  score?: number;
  clause_reference?: string;
}

export interface DocumentAnalysisMetadata {
  document_id?: string;
  doc_type?: string;
  title?: string;
  original_text?: string;
  summary?: string;
  clauses?: DocumentClause[];
  risks?: DocumentRisk[];
  needs_expert_review?: boolean;
  // 리스크 분석 관련 추가 필드
  overall_risk_score?: number;
  severity?: string;
  risk_summary?: string;
  recommendations?: string[];
  // 기존 문서 여부 (true면 이미 저장된 문서)
  is_existing?: boolean;
}

export interface MessageMetadata {
  workflows?: string[];
  executionTime?: number;
  sources?: MessageSource[];
  tokensUsed?: number;
  model?: string;
  intent?: string;
  confidence?: number;
  status?: string;
  documentAnalysis?: DocumentAnalysisMetadata;
}

/**
 * 메시지 소스 (참고 자료)
 */
export interface MessageSource {
  id?: string;
  title: string;
  url?: string;
  type?: 'precedent' | 'law' | 'document' | 'web';
  snippet?: string;
  relevanceScore?: number;
  // RAG workflow에서 반환되는 추가 필드들
  content?: string;
  source?: string;
  score?: number;
  doc_type?: string;
  court?: string;
  date?: string;
  case_number?: string;
}

/**
 * 채팅 메시지
 */
export interface ChatMessage {
  id: string;
  sessionId: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  metadata?: MessageMetadata;
  isStreaming?: boolean;
  attachments?: MessageAttachment[];
}

/**
 * 메시지 첨부 파일
 */
export interface MessageAttachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url?: string;
}

/**
 * 채팅 세션
 */
export interface ChatSession {
  id: string;
  userId: string;
  title: string;
  projectId?: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount: number;
  lastMessage?: string;
  isArchived?: boolean;
  tags?: string[];
}

/**
 * 채팅 요청
 */
export interface AttachmentPayload {
  type: 'file' | 'url' | 'document';
  filename?: string;
  mime_type?: string;
  url?: string;
  size?: number;
  doc_type?: string;
  document_id?: string;
  content?: string;
  metadata?: Record<string, any>;
}

export interface ChatRequest {
  sessionId?: string;
  message: string;
  stream?: boolean;
  attachments?: AttachmentPayload[];
  options?: ChatRequestOptions;
}

/**
 * 채팅 요청 옵션
 */
export interface ChatRequestOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
  includeHistory?: boolean;
  historyLimit?: number;
}

/**
 * 채팅 응답
 */
export interface ChatResponse {
  id: string;
  sessionId: string;
  message: ChatMessage;
  metadata?: ChatResponseMetadata;
}

/**
 * 채팅 응답 메타데이터
 */
export interface ChatResponseMetadata {
  totalTokens?: number;
  promptTokens?: number;
  completionTokens?: number;
  processingTime?: number;
  model?: string;
}

/**
 * SSE 스트리밍 이벤트
 */
export interface SSEEvent {
  type: 'content' | 'metadata' | 'workflow' | 'source' | 'error' | 'done';
  data: unknown;
}

/**
 * SSE 콘텐츠 이벤트
 */
export interface SSEContentEvent {
  type: 'content';
  data: {
    content: string;
    delta?: string;
  };
}

/**
 * SSE 메타데이터 이벤트
 */
export interface SSEMetadataEvent {
  type: 'metadata';
  data: MessageMetadata;
}

/**
 * SSE 워크플로우 이벤트
 */
export interface SSEWorkflowEvent {
  type: 'workflow';
  data: {
    name: string;
    status: 'started' | 'completed' | 'failed';
    progress?: number;
  };
}

/**
 * SSE 에러 이벤트
 */
export interface SSEErrorEvent {
  type: 'error';
  data: {
    code: string;
    message: string;
  };
}

/**
 * 세션 생성 요청
 */
export interface CreateSessionRequest {
  title?: string;
  projectId?: string;
  tags?: string[];
}

/**
 * 세션 업데이트 요청
 */
export interface UpdateSessionRequest {
  title?: string;
  projectId?: string;
  tags?: string[];
  isArchived?: boolean;
}

/**
 * 세션 목록 응답
 */
export interface SessionListResponse {
  sessions: ChatSession[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

/**
 * 프로젝트
 */
export interface Project {
  id: string;
  name: string;
  description?: string;
  color?: string;
  createdAt: Date;
  updatedAt: Date;
  sessionCount?: number;
}

/**
 * 추천 질문
 */
export interface SuggestedQuestion {
  id: string;
  text: string;
  category?: string;
  priority?: number;
}

/**
 * 실행 상태
 */
export interface ExecutionStatus {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: number;
  startedAt?: Date;
  completedAt?: Date;
  error?: string;
}

/**
 * Agent Hub 전역 상태
 */
export interface AgentHubState {
  currentSession: ChatSession | null;
  sessions: ChatSession[];
  messages: ChatMessage[];
  isLoading: boolean;
  isStreaming: boolean;
  error: Error | null;
  suggestedQuestions: SuggestedQuestion[];
  executionStatus: ExecutionStatus[];
}

/**
 * Agent Hub 컨텍스트 타입
 */
export interface AgentHubContextType extends AgentHubState {
  sendMessage: (content: string, attachments?: File[]) => Promise<void>;
  createSession: (request?: CreateSessionRequest) => Promise<ChatSession>;
  switchSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  updateSession: (sessionId: string, data: UpdateSessionRequest) => Promise<void>;
  clearMessages: () => void;
  stopStreaming: () => void;
  retryLastMessage: () => Promise<void>;
}
