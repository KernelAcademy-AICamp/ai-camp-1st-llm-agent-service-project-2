/**
 * Agent Hub Service
 *
 * Agent Hub API 클라이언트
 * SSE 연결 헬퍼
 * 인증 토큰 관리
 */

import {
  ChatMessage,
  ChatSession,
  ChatRequest,
  ChatResponse,
  CreateSessionRequest,
  UpdateSessionRequest,
  SessionListResponse,
  SuggestedQuestion,
  MessageMetadata,
} from '../types/agentHub';

/**
 * Progress 이벤트 데이터 타입
 */
export interface ProgressEvent {
  step: 'ANALYZING' | 'PLANNING' | 'SEARCHING' | 'EXECUTING' | 'THINKING' | 'GENERATING' | 'COMPLETED';
  percentage: number;
  message: string;
  execution_path?: 'fast' | 'medium' | 'deep' | 'thinking';
  step_details?: Record<string, any>;
}

/**
 * 도구 실행 상태 타입
 */
export type ToolExecutionStatus = 'pending' | 'running' | 'completed' | 'failed';

/**
 * 도구 실행 이벤트 데이터 타입
 */
export interface ToolExecutionEvent {
  step: number;
  tool: string;
  category: string;
  description?: string;
  status: ToolExecutionStatus;
  input_preview?: string;
  result_preview?: string;
  execution_time?: number;
  reason?: string;
  success?: boolean;
}

/**
 * 도구 이름에서 카테고리 추출
 */
function _getToolCategory(toolName: string): string {
  const toolCategories: Record<string, string> = {
    'search_legal': 'search',
    'search_precedents': 'search',
    'search_statutes': 'search',
    'rag_workflow': 'search',
    'document_workflow': 'document',
    'analyze_document': 'document',
    'case_workflow': 'analysis',
    'risk_workflow': 'analysis',
    'get_user_cases': 'utility',
    'get_user_documents': 'utility',
  };
  return toolCategories[toolName] || 'utility';
}

/**
 * 도구 이름에서 사용자 친화적 설명 추출
 */
function _getToolDescription(toolName: string): string {
  const toolDescriptions: Record<string, string> = {
    'search_legal': '법률 정보를 검색하고 있습니다...',
    'search_precedents': '관련 판례를 검색하고 있습니다...',
    'search_statutes': '관련 법령을 검색하고 있습니다...',
    'rag_workflow': '법률 정보를 검색하고 있습니다...',
    'document_workflow': '문서를 분석하고 있습니다...',
    'analyze_document': '문서를 분석하고 있습니다...',
    'case_workflow': '판례를 분석하고 있습니다...',
    'risk_workflow': '리스크를 평가하고 있습니다...',
    'get_user_cases': '사건 정보를 조회하고 있습니다...',
    'get_user_documents': '문서 정보를 조회하고 있습니다...',
  };
  return toolDescriptions[toolName] || `${toolName} 실행 중...`;
}

interface PreprocessAttachmentResponse {
  success: boolean;
  text?: string;
  metadata?: Record<string, any>;
  file_type?: string;
}

interface SessionApiModel {
  session_id: string;
  created_at: string;
  expires_at: string;
  organization_id?: string | null;
  project_id?: string | null;
  title?: string | null;
  updated_at?: string | null;
  message_count: number;
  last_message?: string | null;
  user_id?: string | null;
}

interface SessionListApiResponse {
  sessions: SessionApiModel[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

interface HistoryApiResponse {
  session_id: string;
  messages: Array<{
    role: string;
    content: string;
    timestamp: string;
    metadata?: MessageMetadata;
  }>;
  total_messages: number;
}

/**
 * 날짜 문자열을 Date 객체로 변환
 * PostgreSQL은 timestamp with timezone을 세션 타임존(KST)으로 반환하므로,
 * 타임존 정보가 없는 경우 KST(+09:00)로 간주합니다.
 */
const parseUTCDate = (dateStr: string | null | undefined): Date => {
  if (!dateStr) return new Date();
  // 이미 타임존 정보가 있으면 그대로 파싱
  if (dateStr.endsWith('Z') || dateStr.includes('+') || /\d{2}:\d{2}:\d{2}-\d{2}/.test(dateStr)) {
    return new Date(dateStr);
  }
  // 타임존 정보가 없으면 KST(UTC+9)로 간주
  return new Date(dateStr + '+09:00');
};

const mapSession = (session: SessionApiModel): ChatSession => ({
  id: session.session_id,
  userId: session.user_id ?? '',
  title: session.title || '새 대화',
  projectId: session.project_id || undefined,
  createdAt: parseUTCDate(session.created_at),
  updatedAt: parseUTCDate(session.updated_at || session.created_at),
  messageCount: session.message_count ?? 0,
  lastMessage: session.last_message || undefined,
});

// API 기본 URL
const API_BASE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';
const API_PREFIX = '/v2/agent-hub';  // Backend는 /api 없이 직접 라우팅

/**
 * 토큰 가져오기
 */
function getAuthToken(): string | null {
  return localStorage.getItem('lawlaw_auth_token');
}

/**
 * API 요청 헬퍼
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${API_PREFIX}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Unknown error' }));
    throw new Error(error.message || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Agent Hub Service
 */
export const agentHubService = {
  /**
   * 세션 관리
   */
  sessions: {
    /**
     * 세션 목록 조회
     */
    list: async (
      page: number = 1,
      pageSize: number = 20,
      projectId?: string
    ): Promise<SessionListResponse> => {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        ...(projectId && { project_id: projectId }),
      });

      const response = await apiRequest<SessionListApiResponse>(`/sessions?${params}`);
      return {
        sessions: (response.sessions || []).map(mapSession),
        total: response.total,
        page: response.page,
        pageSize: response.page_size,
        hasMore: response.has_next,
      };
    },

    /**
     * 세션 생성
     */
    create: async (request?: CreateSessionRequest): Promise<ChatSession> => {
      const response = await apiRequest<SessionApiModel>('/sessions', {
        method: 'POST',
        body: JSON.stringify(request || {}),
      });
      return mapSession(response);
    },

    /**
     * 세션 조회
     */
    get: async (sessionId: string): Promise<ChatSession> => {
      const response = await apiRequest<SessionApiModel>(`/sessions/${sessionId}`);
      return mapSession(response);
    },

    /**
     * 세션 업데이트
     */
    update: async (
      sessionId: string,
      data: UpdateSessionRequest
    ): Promise<ChatSession> => {
      const response = await apiRequest<SessionApiModel>(`/sessions/${sessionId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      });
      return mapSession(response);
    },

    /**
     * 세션 삭제
     */
    delete: async (sessionId: string): Promise<void> => {
      await apiRequest<void>(`/sessions/${sessionId}`, {
        method: 'DELETE',
      });
    },

    /**
     * 세션 히스토리 조회
     */
    getHistory: async (
      sessionId: string,
      limit: number = 50
    ): Promise<ChatMessage[]> => {
      const response = await apiRequest<HistoryApiResponse>(
        `/sessions/${sessionId}/history?limit=${limit}`
      );

      return (response.messages || []).map((msg, index) => ({
        id: `${response.session_id}-${index}-${msg.timestamp}`,
        sessionId: response.session_id,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: parseUTCDate(msg.timestamp),
        metadata: msg.metadata,
      }));
    },
  },

  /**
   * 채팅 관리
   */
  chat: {
    /**
     * 메시지 전송 (일반)
     */
    send: async (request: ChatRequest): Promise<ChatResponse> => {
      return apiRequest<ChatResponse>('/chat', {
        method: 'POST',
        body: JSON.stringify({
          ...request,
          stream: false,
        }),
      });
    },

    /**
     * 메시지 전송 (스트리밍)
     */
    sendStream: (
      request: ChatRequest,
      callbacks: {
        onContent?: (content: string, accumulated: string) => void;
        onMetadata?: (metadata: MessageMetadata) => void;
        onWorkflow?: (workflow: string) => void;
        onSource?: (sources: Array<{ title: string; url?: string }>) => void;
        onError?: (error: Error) => void;
        onComplete?: (message: ChatMessage) => void;
        onTitleGenerated?: (title: string) => void;
        onProgress?: (progress: ProgressEvent) => void;  // 진행 상태 콜백
        onToolExecution?: (event: ToolExecutionEvent) => void;  // 도구 실행 콜백
      }
    ): AbortController => {
      const abortController = new AbortController();
      const token = getAuthToken();

      (async () => {
        try {
          const response = await fetch(`${API_BASE_URL}${API_PREFIX}/chat`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Accept: 'text/event-stream',
              ...(token && { Authorization: `Bearer ${token}` }),
            },
            body: JSON.stringify({
              ...request,
              stream: true,
            }),
            signal: abortController.signal,
          });

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const reader = response.body?.getReader();
          if (!reader) {
            throw new Error('No response body');
          }

          const decoder = new TextDecoder();
          let accumulatedContent = '';
          let metadata: MessageMetadata = {};
          let messageId = '';
          let sessionId = request.sessionId || '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);

                if (data === '[DONE]') {
                  continue;
                }

                try {
                  const parsed = JSON.parse(data);
                  const eventType = parsed.event;
                  const eventData = parsed.data || {};

                  // 모든 이벤트 타입 로깅 (tool 관련)
                  console.log('[DEBUG] SSE event:', eventType, eventData);

                  // start 이벤트 - 세션 ID 추출
                  if (eventType === 'start') {
                    if (eventData.session_id) {
                      sessionId = eventData.session_id;
                    }
                    if (eventData.message_id) {
                      messageId = eventData.message_id;
                    }
                  }

                  // intent_classified 이벤트
                  if (eventType === 'intent_classified') {
                    metadata.intent = eventData.category;
                    metadata.confidence = eventData.confidence;
                    callbacks.onMetadata?.(metadata);

                    // 법률 관련 질문이면 즉시 "검색 중" 상태 표시
                    // LangGraph 노드 완료를 기다리지 않고 프론트엔드에서 선제적으로 표시
                    const legalCategories = ['QUERY', 'SEARCH', 'CASE_ANALYSIS', 'DOCUMENT_ANALYSIS', 'RISK_ASSESSMENT'];
                    if (legalCategories.includes(eventData.category)) {
                      console.log('[DEBUG] Legal intent detected, showing search indicator');
                      callbacks.onToolExecution?.({
                        step: 0,
                        tool: 'search_legal',
                        category: 'search',
                        description: '법률 정보를 검색하고 있습니다...',
                        status: 'running',
                        input_preview: '관련 법률 정보 검색 중',
                      });
                    }
                  }

                  // execution_plan 이벤트
                  if (eventType === 'execution_plan') {
                    metadata.workflows = eventData.workflows || [];
                    callbacks.onMetadata?.(metadata);
                  }

                  // workflow_started 이벤트
                  if (eventType === 'workflow_started') {
                    callbacks.onWorkflow?.(eventData.workflow);
                  }

                  // workflow_completed 이벤트
                  if (eventType === 'workflow_completed') {
                    // 워크플로우 완료 시 진행 상황 업데이트
                  }

                  // response_generating 이벤트 - 응답 생성 중 표시
                  if (eventType === 'response_generating') {
                    // 로딩 상태 유지
                  }

                  // progress 이벤트 - 진행 상태 업데이트
                  if (eventType === 'progress') {
                    // 백엔드는 소문자로 보내므로 대문자로 변환
                    const stepMapping: Record<string, ProgressEvent['step']> = {
                      'analyzing': 'ANALYZING',
                      'classifying': 'ANALYZING',  // classifying -> ANALYZING로 매핑
                      'planning': 'PLANNING',
                      'searching': 'SEARCHING',
                      'executing': 'EXECUTING',
                      'thinking': 'THINKING',
                      'generating': 'GENERATING',
                      'complete': 'COMPLETED',
                    };
                    const rawStep = (eventData.step || 'executing').toLowerCase();
                    const mappedStep = stepMapping[rawStep] || 'EXECUTING';

                    const progressData: ProgressEvent = {
                      step: mappedStep,
                      percentage: eventData.percentage || 0,
                      message: eventData.message || '처리 중...',
                      execution_path: eventData.execution_path,
                      step_details: eventData.step_details,
                    };
                    callbacks.onProgress?.(progressData);
                  }

                  // tool_selected 이벤트 - 도구 선택됨
                  if (eventType === 'tool_selected') {
                    callbacks.onToolExecution?.({
                      step: eventData.step,
                      tool: eventData.tool,
                      category: eventData.category || 'unknown',
                      description: eventData.description,
                      status: 'pending',
                      input_preview: eventData.input_preview,
                      reason: eventData.reason,
                    });
                  }

                  // tool_execution_start 이벤트 - 도구 실행 시작
                  if (eventType === 'tool_execution_start') {
                    callbacks.onToolExecution?.({
                      step: eventData.step,
                      tool: eventData.tool,
                      category: eventData.category || 'unknown',
                      description: eventData.description,
                      status: 'running',
                      input_preview: eventData.input_preview,
                    });
                  }

                  // tools_selected 이벤트 - 도구 선택 완료, "검색 중" 표시 시작
                  if (eventType === 'tools_selected') {
                    const selectedTools = eventData.tools || [];
                    console.log('[DEBUG] tools_selected event received:', { selectedTools, eventData });

                    // 첫 번째 도구를 "검색 중" 상태로 표시
                    if (selectedTools.length > 0) {
                      const primaryTool = selectedTools.includes('search_legal')
                        ? 'search_legal'
                        : selectedTools[0];
                      callbacks.onToolExecution?.({
                        step: 0,
                        tool: primaryTool,
                        category: _getToolCategory(primaryTool),
                        description: eventData.message || _getToolDescription(primaryTool),
                        status: 'running',
                        input_preview: `선택된 도구: ${selectedTools.join(', ')}`,
                      });
                    }
                  }

                  // tool_call 이벤트 - LLM Native Tool Use Agent에서 도구 호출 시작
                  if (eventType === 'tool_call') {
                    const toolName = eventData.tool_name || eventData.tool || 'unknown';
                    const args = eventData.arguments || {};
                    console.log('[DEBUG] tool_call event received:', { toolName, args, eventData });
                    callbacks.onToolExecution?.({
                      step: eventData.iteration || 1,
                      tool: toolName,
                      category: _getToolCategory(toolName),
                      description: _getToolDescription(toolName),
                      status: 'running',
                      input_preview: JSON.stringify(args).slice(0, 100),
                    });
                  }

                  // tool_execution_complete 이벤트 - 도구 실행 완료
                  if (eventType === 'tool_execution_complete') {
                    callbacks.onToolExecution?.({
                      step: eventData.step,
                      tool: eventData.tool,
                      category: eventData.category || 'unknown',
                      status: eventData.success ? 'completed' : 'failed',
                      success: eventData.success,
                      execution_time: eventData.execution_time,
                      result_preview: eventData.result_preview,
                    });
                  }

                  // tool_result 이벤트 - LLM Native Tool Use Agent에서 도구 실행 완료
                  if (eventType === 'tool_result') {
                    const toolName = eventData.tool_name || eventData.tool || 'unknown';
                    callbacks.onToolExecution?.({
                      step: eventData.iteration || 1,
                      tool: toolName,
                      category: _getToolCategory(toolName),
                      status: eventData.success ? 'completed' : 'failed',
                      success: eventData.success,
                      execution_time: eventData.execution_time,
                      result_preview: eventData.result_preview || '결과 확인됨',
                    });
                  }

                  // complete 이벤트 - 최종 응답
                  if (eventType === 'complete') {
                    const response = eventData.response || '';
                    accumulatedContent = response;
                    callbacks.onContent?.(response, response);

                    // 메타데이터 업데이트
                    metadata.executionTime = eventData.execution_time;
                    metadata.workflows = eventData.workflows_executed || [];
                    metadata.status = eventData.status;
                    if (eventData.document_analysis) {
                      metadata.documentAnalysis = eventData.document_analysis;
                    }
                    callbacks.onMetadata?.(metadata);

                    // sources(참고자료) 처리
                    console.log('[DEBUG] complete eventData:', eventData);
                    console.log('[DEBUG] eventData.sources:', eventData.sources);
                    if (eventData.sources && eventData.sources.length > 0) {
                      console.log('[DEBUG] Setting sources:', eventData.sources);
                      metadata.sources = eventData.sources;
                      callbacks.onSource?.(eventData.sources);
                    } else {
                      console.log('[DEBUG] No sources in complete event');
                    }
                  }

                  // done 이벤트 - 완료 및 세션 제목
                  if (eventType === 'done') {
                    // 세션 ID 업데이트
                    if (eventData.session_id) {
                      sessionId = eventData.session_id;
                    }
                    // 자동 생성된 제목 콜백
                    if (eventData.title && callbacks.onTitleGenerated) {
                      callbacks.onTitleGenerated(eventData.title);
                    }
                  }

                  // error 이벤트
                  if (eventType === 'error') {
                    const errorMsg = eventData.message || 'Unknown error';
                    callbacks.onError?.(new Error(errorMsg));
                  }

                  // heartbeat 이벤트 - 연결 유지용 (무시)
                  // heartbeat는 연결 유지 목적이므로 progress 업데이트하지 않음
                  if (eventType === 'heartbeat') {
                    // 연결 유지를 위한 heartbeat, 별도 처리 불필요
                    // progress를 0으로 재설정하지 않도록 무시
                  }

                  // 레거시 형식 지원 (직접 content 필드)
                  if (parsed.content && !eventType) {
                    accumulatedContent += parsed.content;
                    callbacks.onContent?.(parsed.content, accumulatedContent);
                  }

                  // 레거시 세션 ID
                  if (parsed.session_id && !eventType) {
                    sessionId = parsed.session_id;
                  }

                  // 레거시 소스 정보
                  if (parsed.sources) {
                    metadata.sources = parsed.sources;
                    callbacks.onSource?.(parsed.sources);
                  }
                } catch (e) {
                  // JSON 파싱 실패 시 일반 텍스트로 처리
                  if (data.trim()) {
                    accumulatedContent += data;
                    callbacks.onContent?.(data, accumulatedContent);
                  }
                }
              }
            }
          }

          // 완료 콜백
          const finalMessage: ChatMessage = {
            id: messageId || `msg-${Date.now()}`,
            sessionId,
            role: 'assistant',
            content: accumulatedContent,
            timestamp: new Date(),
            metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
          };

          callbacks.onComplete?.(finalMessage);
        } catch (error) {
          if ((error as Error).name !== 'AbortError') {
            callbacks.onError?.(error as Error);
          }
        }
      })();

      return abortController;
    },
  },

  /**
   * 추천 질문 조회
   */
  getSuggestedQuestions: async (
    sessionId?: string,
    limit: number = 5
  ): Promise<SuggestedQuestion[]> => {
    const params = new URLSearchParams({
      limit: limit.toString(),
      ...(sessionId && { session_id: sessionId }),
    });

    return apiRequest<SuggestedQuestion[]>(`/suggestions?${params}`);
  },

  /**
   * 대화 요약 생성
   */
  generateSummary: async (sessionId: string): Promise<string> => {
    const response = await apiRequest<{ summary: string }>(
      `/sessions/${sessionId}/summary`,
      { method: 'POST' }
    );
    return response.summary;
  },

  /**
   * 관련 판례 검색
   */
  searchRelatedCases: async (
    query: string,
    limit: number = 5
  ): Promise<Array<{ title: string; url: string; relevance: number }>> => {
    const params = new URLSearchParams({
      q: query,
      limit: limit.toString(),
    });

    return apiRequest<Array<{ title: string; url: string; relevance: number }>>(
      `/search/cases?${params}`
    );
  },

  /**
   * 분석 결과 Documents에 저장
   */
  saveAnalysis: async (request: {
    sessionId: string;
    messageId?: string;
    title: string;
    docType?: string;
    originalText: string;
    summary?: string;
    clauses?: Array<{
      clause_type: string;
      title: string;
      content: string;
      importance_score: number;
    }>;
    riskAnalysis?: {
      overall_risk_score: number;
      severity: string;
      risk_items: Array<any>;
      recommendations: string[];
      summary: string;
    };
  }): Promise<{
    success: boolean;
    document_id: string;
    document_url: string;
    message: string;
    saved_items: Record<string, boolean>;
  }> => {
    return apiRequest('/save-analysis', {
      method: 'POST',
      body: JSON.stringify({
        session_id: request.sessionId,
        message_id: request.messageId,
        title: request.title,
        doc_type: request.docType || 'OTHER',
        original_text: request.originalText,
        summary: request.summary,
        clauses: request.clauses,
        risk_analysis: request.riskAnalysis,
      }),
    });
  },

  attachments: {
    preprocess: async (file: File): Promise<PreprocessAttachmentResponse> => {
      const formData = new FormData();
      formData.append('file', file);

      const token = getAuthToken();
      const headers: HeadersInit = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/preprocess/document`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to preprocess document' }));
        throw new Error(error.detail || 'Failed to preprocess document');
      }

      return response.json();
    },
  },
};

/**
 * SSE 연결 헬퍼
 */
export class SSEConnection {
  private eventSource: EventSource | null = null;
  private url: string;
  private callbacks: {
    onMessage?: (event: MessageEvent) => void;
    onError?: (event: Event) => void;
    onOpen?: () => void;
  };

  constructor(
    endpoint: string,
    callbacks: {
      onMessage?: (event: MessageEvent) => void;
      onError?: (event: Event) => void;
      onOpen?: () => void;
    } = {}
  ) {
    const token = getAuthToken();
    const url = new URL(`${API_BASE_URL}${API_PREFIX}${endpoint}`);
    if (token) {
      url.searchParams.set('token', token);
    }
    this.url = url.toString();
    this.callbacks = callbacks;
  }

  connect(): void {
    if (this.eventSource) {
      this.disconnect();
    }

    this.eventSource = new EventSource(this.url);

    this.eventSource.onopen = () => {
      this.callbacks.onOpen?.();
    };

    this.eventSource.onmessage = (event) => {
      this.callbacks.onMessage?.(event);
    };

    this.eventSource.onerror = (event) => {
      this.callbacks.onError?.(event);
    };
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }
}

export default agentHubService;
