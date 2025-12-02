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

const mapSession = (session: SessionApiModel): ChatSession => ({
  id: session.session_id,
  userId: session.user_id ?? '',
  title: session.title || '새 대화',
  projectId: session.project_id || undefined,
  createdAt: new Date(session.created_at),
  updatedAt: new Date(session.updated_at || session.created_at || Date.now()),
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
        timestamp: new Date(msg.timestamp),
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
        onTitleGenerated?: (title: string) => void;  // 제목 생성 콜백 추가
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
                    if (eventData.sources && eventData.sources.length > 0) {
                      metadata.sources = eventData.sources;
                      callbacks.onSource?.(eventData.sources);
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
