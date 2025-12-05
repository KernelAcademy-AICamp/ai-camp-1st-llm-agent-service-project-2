/**
 * Agent Hub - Main Page
 *
 * AI 기반 법률 자문 채팅 인터페이스
 * AppLayout 사용, useChat 훅으로 상태 관리
 * SSE 스트리밍 처리
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

// Agent Hub Components
import { AppLayout } from '../../components/agent-hub/layout';
import { MessageList, Message } from '../../components/agent-hub/messages';
import type { DocumentAnalysisMetadata } from '../../types/agentHub';

// Services
import { agentHubService, ProgressEvent, ToolExecutionEvent } from '../../services/agentHubService';
import { ChatSession, SuggestedQuestion, AttachmentPayload } from '../../types/agentHub';

// Types
import type { ExecutionStatus } from '../../components/agent-hub/layout/AppLayout';

// Styles
import './AgentHub.css';

const LAST_SESSION_STORAGE_KEY = 'agentHub:lastSessionId';

/**
 * Agent Hub 메인 페이지
 */
const AgentHub: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isLoading: authLoading } = useAuth();

  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [suggestedQuestions, setSuggestedQuestions] = useState<SuggestedQuestion[]>([]);
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatus | null>(null);
  const [toolExecutions, setToolExecutions] = useState<ToolExecutionEvent[]>([]);

  // Refs
  const abortControllerRef = useRef<AbortController | null>(null);

  const refreshSessions = useCallback(async (): Promise<ChatSession[]> => {
    try {
      const sessionsResponse = await agentHubService.sessions.list();
      const apiSessions = sessionsResponse?.sessions ?? [];
      setSessions(apiSessions);
      return apiSessions;
    } catch (err) {
      console.error('Failed to load sessions from API:', err);
      setSessions([]);
      return [];
    }
  }, []);

  const loadSession = useCallback(
    async (id: string) => {
      try {
        setIsLoading(true);
        setError(null);
        setSessionId(id);
        setMessages([]);

        // API에서 히스토리 로드
        const history = await agentHubService.sessions.getHistory(id);
        const mappedMessages: Message[] = (history ?? []).map((msg) => ({
          id: msg.id,
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          metadata: msg.metadata,
        }));
        setMessages(mappedMessages);
      } catch (err) {
        console.error('Failed to load session:', err);
        setMessages([]);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  // 초기 데이터 로드
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const sessionsList = await refreshSessions();

        const urlSessionId = searchParams.get('session');
        const lastSessionId =
          typeof window !== 'undefined'
            ? window.localStorage.getItem(LAST_SESSION_STORAGE_KEY)
            : null;

        // 세션 ID 우선순위: URL > localStorage > 첫 번째 세션
        let targetSessionId = urlSessionId || lastSessionId;

        // 저장된 세션 ID가 실제로 존재하는지 확인
        if (targetSessionId && sessionsList.length > 0) {
          const sessionExists = sessionsList.some((s) => s.id === targetSessionId);
          if (!sessionExists) {
            // 저장된 세션이 삭제된 경우, 첫 번째 세션으로 fallback
            targetSessionId = sessionsList[0]?.id || null;
            // 잘못된 세션 ID 정리
            if (typeof window !== 'undefined') {
              window.localStorage.removeItem(LAST_SESSION_STORAGE_KEY);
            }
          }
        } else if (!targetSessionId && sessionsList.length > 0) {
          targetSessionId = sessionsList[0].id;
        }

        if (targetSessionId) {
          await loadSession(targetSessionId);
          // URL 업데이트
          if (targetSessionId !== urlSessionId) {
            navigate(`/agent-hub?session=${targetSessionId}`, { replace: true });
          }
        }

        const questions = await agentHubService.getSuggestedQuestions();
        setSuggestedQuestions(questions);
      } catch (err) {
        console.error('Failed to load initial data:', err);
      }
    };

    if (!authLoading) {
      loadInitialData();
    }
  }, [authLoading, loadSession, navigate, refreshSessions, searchParams]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (sessionId) {
      window.localStorage.setItem(LAST_SESSION_STORAGE_KEY, sessionId);
    } else {
      window.localStorage.removeItem(LAST_SESSION_STORAGE_KEY);
    }
  }, [sessionId]);

  // 새 세션 생성
  const createNewSession = useCallback(async () => {
    try {
      const newSession = await agentHubService.sessions.create({
        title: '새 대화',
      });
      setSessionId(newSession.id);
      setMessages([]);
      setSessions((prev) => [newSession, ...prev.filter((s) => s.id !== newSession.id)]);
      navigate(`/agent-hub?session=${newSession.id}`);
      await refreshSessions();
    } catch (err) {
      console.error('Failed to create session:', err);
      setError(new Error('세션 생성에 실패했습니다. 다시 시도해주세요.'));
    }
  }, [navigate, refreshSessions]);

  // 메시지 전송
  const handleSendMessage = useCallback(
    async (content: string, attachments?: AttachmentPayload[]) => {
      if (!content.trim() && (!attachments || attachments.length === 0)) {
        return;
      }

      setError(null);
      setIsLoading(true);

      let activeSessionId = sessionId;
      if (!activeSessionId) {
        try {
          const newSession = await agentHubService.sessions.create({
            title: content.slice(0, 30) || '새 대화',
          });
          activeSessionId = newSession.id;
          setSessionId(newSession.id);
          setSessions((prev) => [newSession, ...prev.filter((s) => s.id !== newSession.id)]);
          navigate(`/agent-hub?session=${newSession.id}`);
        } catch (err) {
          console.error('Failed to create session before sending:', err);
          setError(new Error('세션 생성에 실패했습니다. 다시 시도해주세요.'));
          setIsLoading(false);
          return;
        }
      }

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

      setIsStreaming(true);
      setToolExecutions([]);  // 도구 실행 로그 초기화
      setExecutionStatus({
        name: '분석 중...',
        step: 'ANALYZING',
        progress: 5,
        message: '질문을 분석하고 있습니다...',
        toolExecutions: [],
      });

      // SSE 스트리밍 시작
      abortControllerRef.current = agentHubService.chat.sendStream(
        {
          sessionId: activeSessionId || undefined,
          message: content,
          stream: true,
          attachments,
        },
        {
          onContent: (delta, accumulated) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId ? { ...msg, content: accumulated } : msg
              )
            );
          },
          onMetadata: (metadata) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, metadata: { ...msg.metadata, ...metadata } }
                  : msg
              )
            );
          },
          onWorkflow: (workflow) => {
            setExecutionStatus((prev) => ({
              ...prev,
              name: `${workflow} 실행 중...`,
              step: 'EXECUTING',
              message: `${workflow} 워크플로우를 실행하고 있습니다...`,
            }));
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      metadata: {
                        ...msg.metadata,
                        workflows: [...(msg.metadata?.workflows || []), workflow],
                      },
                    }
                  : msg
              )
            );
          },
          onProgress: (progressEvent: ProgressEvent) => {
            // Progress 이벤트로 실행 상태 업데이트
            setExecutionStatus((prev) => ({
              name: progressEvent.message,
              step: progressEvent.step,
              progress: progressEvent.percentage,
              message: progressEvent.message,
              execution_path: progressEvent.execution_path,
              step_details: progressEvent.step_details,
              toolExecutions: prev?.toolExecutions || [],
            }));
          },
          onToolExecution: (toolEvent: ToolExecutionEvent) => {
            // 도구 실행 이벤트 처리
            console.log('[DEBUG AgentHub] onToolExecution called:', toolEvent);
            setToolExecutions((prev) => {
              // 같은 step + tool 조합의 이벤트 업데이트 또는 추가
              const existingIndex = prev.findIndex(
                (e) => e.step === toolEvent.step && e.tool === toolEvent.tool
              );
              if (existingIndex >= 0) {
                const updated = [...prev];
                updated[existingIndex] = toolEvent;
                return updated;
              }
              return [...prev, toolEvent];
            });
            // executionStatus의 toolExecutions도 업데이트
            setExecutionStatus((prev) => {
              if (!prev) return prev;
              const currentExecutions = prev.toolExecutions || [];
              const existingIndex = currentExecutions.findIndex(
                (e) => e.step === toolEvent.step && e.tool === toolEvent.tool
              );
              let newExecutions: ToolExecutionEvent[];
              if (existingIndex >= 0) {
                newExecutions = [...currentExecutions];
                newExecutions[existingIndex] = toolEvent;
              } else {
                newExecutions = [...currentExecutions, toolEvent];
              }
              return { ...prev, toolExecutions: newExecutions };
            });
          },
          onSource: (sources) => {
            console.log('[DEBUG AgentHub] onSource called with:', sources);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, metadata: { ...msg.metadata, sources } }
                  : msg
              )
            );
          },
          onError: (err) => {
            setError(err);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      isStreaming: false,
                      content:
                        msg.content ||
                        '죄송합니다. 응답을 생성하는 중 오류가 발생했습니다.',
                    }
                  : msg
              )
            );
          },
          onComplete: (finalMessage) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      content: finalMessage.content,
                      metadata: finalMessage.metadata,
                      isStreaming: false,
                    }
                  : msg
              )
            );

            // 세션 ID 업데이트
            if (finalMessage.sessionId) {
              setSessionId(finalMessage.sessionId);
              if (finalMessage.sessionId !== sessionId) {
                navigate(`/agent-hub?session=${finalMessage.sessionId}`, { replace: true });
              }
            }

            // 스트리밍 완료 후 상태 정리
            setIsLoading(false);
            setIsStreaming(false);
            setExecutionStatus(null);
            setToolExecutions([]);  // 도구 실행 로그 초기화 - 완료 후 표시 제거
            abortControllerRef.current = null;

            refreshSessions();
          },
          // 자동 생성된 제목 처리
          onTitleGenerated: (generatedTitle) => {
            const currentSessionId = activeSessionId;
            if (currentSessionId && generatedTitle) {
              // 세션 목록에서 제목 업데이트
              setSessions((prev) =>
                prev.map((s) =>
                  s.id === currentSessionId
                    ? { ...s, title: generatedTitle }
                    : s
                )
              );
            }
          },
        }
      );
    },
    [navigate, refreshSessions, sessionId]
  );

  // 스트리밍 중지
  const handleStopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
      setExecutionStatus(null);
    }
  }, []);

  // 세션 선택
  const handleSelectSession = useCallback(
    async (id: string) => {
      await loadSession(id);
      navigate(`/agent-hub?session=${id}`);
    },
    [loadSession, navigate]
  );

  // 세션 삭제
  const handleDeleteSession = useCallback(
    async (id: string) => {
      try {
        await agentHubService.sessions.delete(id);
      } catch (err) {
        console.error('Failed to delete session:', err);
      }

      // UI 상태 업데이트
      setSessions((prev) => prev.filter((s) => s.id !== id));

      if (sessionId === id) {
        const nextSession = sessions.find((s) => s.id !== id);
        if (nextSession) {
          await loadSession(nextSession.id);
          navigate(`/agent-hub?session=${nextSession.id}`);
        } else {
          setSessionId(null);
          setMessages([]);
          navigate('/agent-hub');
        }
      }
    },
    [loadSession, navigate, sessionId, sessions]
  );

  // 추천 질문 클릭
  const handleSuggestedQuestionClick = useCallback(
    (question: string) => {
      handleSendMessage(question);
    },
    [handleSendMessage]
  );

  // 분석 결과 저장
  const handleSaveAnalysis = useCallback(
    async (message: Message): Promise<{ success: boolean; document_url?: string; error?: string }> => {
      if (!sessionId) {
        return { success: false, error: '세션 ID가 없습니다' };
      }

      const docAnalysis = message.metadata?.documentAnalysis as DocumentAnalysisMetadata | undefined;
      if (!docAnalysis) {
        return { success: false, error: '문서 분석 결과가 없습니다' };
      }

      try {
        // 문서 분석 메타데이터에서 저장할 데이터 추출
        const result = await agentHubService.saveAnalysis({
          sessionId,
          messageId: message.id,
          title: docAnalysis.title || '분석된 문서',
          docType: docAnalysis.doc_type || 'OTHER',
          originalText: docAnalysis.original_text || message.content,
          summary: docAnalysis.summary,
          clauses: docAnalysis.clauses?.map((c) => ({
            clause_type: c.clause_type || 'OTHER',
            title: c.clause_number || c.text?.slice(0, 50) || '조항',
            content: c.text || '',
            importance_score: c.importance_score || 50,
          })),
          riskAnalysis: docAnalysis.risks
            ? {
                overall_risk_score: docAnalysis.overall_risk_score || 50,
                severity: docAnalysis.severity || 'MEDIUM',
                risk_items: docAnalysis.risks.map((r) => ({
                  category: r.category || 'OTHER',
                  title: r.name || '리스크',
                  description: r.description || '',
                  severity: r.severity || 'MEDIUM',
                  score: r.score || 50,
                  clause_reference: r.clause_reference,
                })),
                recommendations: docAnalysis.recommendations || [],
                summary: docAnalysis.risk_summary || '',
              }
            : undefined,
        });

        return {
          success: result.success,
          document_url: result.document_url,
        };
      } catch (error) {
        console.error('Failed to save analysis:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : '저장 중 오류가 발생했습니다',
        };
      }
    },
    [sessionId]
  );

  // 참고: 페이지 이동 시 SSE 스트리밍을 abort하지 않습니다.
  // 백엔드가 응답을 완료하고 DB에 저장하도록 허용합니다.
  // 사용자가 돌아오면 loadSession()에서 완료된 응답을 로드합니다.
  // 사용자가 명시적으로 "중지"를 원하면 handleStopStreaming()을 사용합니다.

  // 로딩 상태
  if (authLoading) {
    return (
      <div className="agent-hub-loading">
        <div className="loading-spinner" />
        <p>로딩 중...</p>
      </div>
    );
  }

  return (
    <AppLayout
      sessions={(sessions ?? []).map((s) => ({
        id: s.id,
        title: s.title,
        lastMessage: s.lastMessage,
        timestamp: s.updatedAt,
        isActive: s.id === sessionId,
      }))}
      currentSessionId={sessionId}
      onNewChat={createNewSession}
      onSelectSession={handleSelectSession}
      onDeleteSession={handleDeleteSession}
      onSendMessage={handleSendMessage}
      onStopStreaming={handleStopStreaming}
      isStreaming={isStreaming}
      executionStatus={executionStatus || undefined}
      suggestedQuestions={(suggestedQuestions ?? []).map((q) => q.text)}
      onSuggestedQuestionClick={handleSuggestedQuestionClick}
    >
      {/* Message List */}
      <MessageList
        messages={messages}
        isLoading={isLoading}
        className="flex-1"
        sessionId={sessionId || undefined}
        onSuggestedQuestionClick={handleSuggestedQuestionClick}
        onSaveAnalysis={handleSaveAnalysis}
        toolExecutions={toolExecutions}
      />

      {/* Error Display */}
      {error && (
        <div className="agent-hub-error">
          <p>{error.message}</p>
          <button onClick={() => setError(null)}>닫기</button>
        </div>
      )}
    </AppLayout>
  );
};

export default AgentHub;
