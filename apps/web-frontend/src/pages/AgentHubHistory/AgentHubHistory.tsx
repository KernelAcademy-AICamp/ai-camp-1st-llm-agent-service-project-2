import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { agentHubService } from '../../services/agentHubService';
import { ChatSession } from '../../types/agentHub';
import './AgentHubHistory.css';

const AgentHubHistory: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const loadSessions = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await agentHubService.sessions.list(1, 100);
        setSessions(response.sessions || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : '검색 기록을 불러오지 못했습니다.');
      } finally {
        setIsLoading(false);
      }
    };

    loadSessions();
  }, []);

  const handleOpenSession = (sessionId: string) => {
    navigate(`/agent-hub?session=${sessionId}`);
  };

  return (
    <div className="agent-hub-history-page">
      <header className="agent-hub-history-header">
        <div>
          <p className="agent-hub-history-eyebrow">AI 어시스턴트</p>
          <h1>검색 기록</h1>
          <p className="agent-hub-history-description">
            최근 대화와 분석 기록을 확인하고 이어서 진행할 수 있습니다.
          </p>
        </div>
      </header>

      {isLoading && (
        <div className="agent-hub-history-state">검색 기록을 불러오는 중입니다...</div>
      )}

      {error && !isLoading && (
        <div className="agent-hub-history-state agent-hub-history-state--error">
          {error}
        </div>
      )}

      {!isLoading && !error && sessions.length === 0 && (
        <div className="agent-hub-history-state">
          아직 저장된 기록이 없습니다. 새로운 대화를 시작해 보세요.
        </div>
      )}

      {!isLoading && !error && sessions.length > 0 && (
        <div className="agent-hub-history-list">
          {sessions.map((session) => (
            <button
              key={session.id}
              className="agent-hub-history-card"
              onClick={() => handleOpenSession(session.id)}
            >
              <div className="agent-hub-history-card__header">
                <h3>{session.title || '제목 없는 대화'}</h3>
                <span className="agent-hub-history-card__timestamp">
                  {session.updatedAt.toLocaleString('ko-KR')}
                </span>
              </div>
              <p className="agent-hub-history-card__preview">
                {session.lastMessage || '최근 메시지가 없습니다.'}
              </p>
              <div className="agent-hub-history-card__meta">
                <span>메시지 {session.messageCount}개</span>
                {session.projectId && <span>프로젝트 {session.projectId}</span>}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default AgentHubHistory;
