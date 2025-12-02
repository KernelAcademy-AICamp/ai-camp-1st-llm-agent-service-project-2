/**
 * Agent Hub - Chat Hook
 *
 * SSE(Server-Sent Events) 연결 관리
 * 메시지 상태 관리
 * 스트리밍 이벤트 처리
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { Message, MessageMetadata } from '../components/agent-hub/messages';

// API 설정
const API_BASE_URL = process.env.REACT_APP_AI_SERVICE_URL || 'http://localhost:8001';

export interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount: number;
}

export interface UseChatOptions {
  sessionId?: string;
  onMessage?: (message: Message) => void;
  onError?: (error: Error) => void;
  onStreamStart?: () => void;
  onStreamEnd?: () => void;
}

export interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  error: Error | null;
  sessionId: string | null;
  sendMessage: (content: string, attachments?: File[]) => Promise<void>;
  clearMessages: () => void;
  retryLastMessage: () => Promise<void>;
  stopStreaming: () => void;
  createNewSession: () => void;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const { onMessage, onError, onStreamStart, onStreamEnd } = options;

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(options.sessionId || null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const lastUserMessageRef = useRef<string>('');

  // 새 세션 생성
  const createNewSession = useCallback(() => {
    setSessionId(`session-${Date.now()}`);
    setMessages([]);
    setError(null);
  }, []);

  // 초기 세션 설정
  useEffect(() => {
    if (!sessionId) {
      createNewSession();
    }
  }, [sessionId, createNewSession]);

  // 메시지 전송
  const sendMessage = useCallback(
    async (content: string, attachments?: File[]) => {
      if (!content.trim() && (!attachments || attachments.length === 0)) {
        return;
      }

      setError(null);
      setIsLoading(true);
      lastUserMessageRef.current = content;

      // 사용자 메시지 추가
      const userMessage: Message = {
        id: `msg-${Date.now()}-user`,
        role: 'user',
        content: content.trim(),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // AI 응답을 위한 빈 메시지 추가 (스트리밍용)
      const aiMessageId = `msg-${Date.now()}-assistant`;
      const aiMessage: Message = {
        id: aiMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };
      setMessages((prev) => [...prev, aiMessage]);

      // SSE 연결
      try {
        abortControllerRef.current = new AbortController();
        setIsStreaming(true);
        onStreamStart?.();

        const response = await fetch(`${API_BASE_URL}/api/v2/agent-hub/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
          },
          body: JSON.stringify({
            session_id: sessionId,
            message: content,
            stream: true,
          }),
          signal: abortControllerRef.current.signal,
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

                // 콘텐츠 청크
                if (parsed.content) {
                  accumulatedContent += parsed.content;
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === aiMessageId
                        ? { ...msg, content: accumulatedContent }
                        : msg
                    )
                  );
                }

                // 메타데이터
                if (parsed.metadata) {
                  metadata = { ...metadata, ...parsed.metadata };
                }

                // 워크플로우 정보
                if (parsed.workflow) {
                  metadata.workflows = [...(metadata.workflows || []), parsed.workflow];
                }

                // 소스 정보
                if (parsed.sources) {
                  metadata.sources = parsed.sources;
                }
              } catch (e) {
                // JSON 파싱 실패 시 일반 텍스트로 처리
                if (data.trim()) {
                  accumulatedContent += data;
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === aiMessageId
                        ? { ...msg, content: accumulatedContent }
                        : msg
                    )
                  );
                }
              }
            }
          }
        }

        // 스트리밍 완료 - 최종 메시지 업데이트
        const finalMessage: Message = {
          id: aiMessageId,
          role: 'assistant',
          content: accumulatedContent,
          timestamp: new Date(),
          isStreaming: false,
          metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
        };

        setMessages((prev) =>
          prev.map((msg) => (msg.id === aiMessageId ? finalMessage : msg))
        );

        onMessage?.(finalMessage);
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          // 사용자가 취소한 경우
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === aiMessageId
                ? { ...msg, isStreaming: false, content: msg.content || '(취소됨)' }
                : msg
            )
          );
        } else {
          const error = err as Error;
          setError(error);
          onError?.(error);

          // 에러 메시지로 업데이트
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === aiMessageId
                ? {
                    ...msg,
                    isStreaming: false,
                    content: '죄송합니다. 응답을 생성하는 중 오류가 발생했습니다.',
                  }
                : msg
            )
          );
        }
      } finally {
        setIsLoading(false);
        setIsStreaming(false);
        abortControllerRef.current = null;
        onStreamEnd?.();
      }
    },
    [sessionId, onMessage, onError, onStreamStart, onStreamEnd]
  );

  // 스트리밍 중지
  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  // 마지막 메시지 재시도
  const retryLastMessage = useCallback(async () => {
    if (!lastUserMessageRef.current) return;

    // 마지막 AI 메시지 제거
    setMessages((prev) => {
      const lastIndex = prev.length - 1;
      if (lastIndex >= 0 && prev[lastIndex].role === 'assistant') {
        return prev.slice(0, lastIndex);
      }
      return prev;
    });

    // 마지막 사용자 메시지도 제거 (다시 추가될 것이므로)
    setMessages((prev) => {
      const lastIndex = prev.length - 1;
      if (lastIndex >= 0 && prev[lastIndex].role === 'user') {
        return prev.slice(0, lastIndex);
      }
      return prev;
    });

    // 재전송
    await sendMessage(lastUserMessageRef.current);
  }, [sendMessage]);

  // 메시지 초기화
  const clearMessages = useCallback(() => {
    stopStreaming();
    setMessages([]);
    setError(null);
    lastUserMessageRef.current = '';
  }, [stopStreaming]);

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    messages,
    isLoading,
    isStreaming,
    error,
    sessionId,
    sendMessage,
    clearMessages,
    retryLastMessage,
    stopStreaming,
    createNewSession,
  };
}

/**
 * useSSE - 범용 SSE 연결 훅
 */
export interface UseSSEOptions<T> {
  url: string;
  onMessage?: (data: T) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  autoConnect?: boolean;
}

export function useSSE<T = unknown>(options: UseSSEOptions<T>) {
  const { url, onMessage, onError, onOpen, autoConnect = true } = options;
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<T | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setIsConnected(true);
      onOpen?.();
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as T;
        setLastEvent(data);
        onMessage?.(data);
      } catch {
        // JSON이 아닌 경우 그대로 전달
        setLastEvent(event.data as unknown as T);
        onMessage?.(event.data as unknown as T);
      }
    };

    eventSource.onerror = (error) => {
      setIsConnected(false);
      onError?.(error);
    };

    eventSourceRef.current = eventSource;
  }, [url, onMessage, onError, onOpen]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    isConnected,
    lastEvent,
    connect,
    disconnect,
  };
}

export default useChat;
