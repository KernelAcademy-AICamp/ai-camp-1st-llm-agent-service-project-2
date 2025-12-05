/**
 * Agent Hub - Inline Tool Indicator Component (ChatGPT Style)
 *
 * 메시지 카드 내에서 도구 사용 상태를 인라인으로 표시
 * ChatGPT의 "웹 검색 중...", "코드 실행 중..." 스타일
 */

import React, { useMemo } from 'react';
import { cn } from '../../../lib/utils';
import type { ToolExecutionEvent, ToolExecutionStatus } from '../../../services/agentHubService';

interface InlineToolIndicatorProps {
  executions: ToolExecutionEvent[];
  className?: string;
  showCompleted?: boolean;
  maxVisible?: number;
}

/**
 * 도구 이름 → 친화적 이름 + 진행형 메시지 매핑
 */
const TOOL_DISPLAY_CONFIG: Record<string, {
  name: string;
  runningMessage: string;
  icon: string;
  category: 'search' | 'analysis' | 'document' | 'external' | 'utility';
}> = {
  // Search Tools
  search_precedents: {
    name: '판례 검색',
    runningMessage: '관련 판례를 검색하고 있습니다',
    icon: '🔍',
    category: 'search',
  },
  search_statutes: {
    name: '법령 검색',
    runningMessage: '관련 법령을 검색하고 있습니다',
    icon: '📚',
    category: 'search',
  },
  search_related_cases: {
    name: '관련 사건 검색',
    runningMessage: '관련 사건을 찾고 있습니다',
    icon: '🔗',
    category: 'search',
  },
  rag_search: {
    name: 'RAG 검색',
    runningMessage: '법률 데이터베이스를 검색하고 있습니다',
    icon: '🔍',
    category: 'search',
  },
  semantic_search: {
    name: '시맨틱 검색',
    runningMessage: '의미 기반 검색을 수행하고 있습니다',
    icon: '🧠',
    category: 'search',
  },
  // Analysis Tools
  analyze_risks: {
    name: '리스크 분석',
    runningMessage: '리스크를 분석하고 있습니다',
    icon: '⚠️',
    category: 'analysis',
  },
  analyze_document: {
    name: '문서 분석',
    runningMessage: '문서를 분석하고 있습니다',
    icon: '📋',
    category: 'document',
  },
  compare_documents: {
    name: '문서 비교',
    runningMessage: '문서를 비교하고 있습니다',
    icon: '⚖️',
    category: 'document',
  },
  extract_clauses: {
    name: '조항 추출',
    runningMessage: '주요 조항을 추출하고 있습니다',
    icon: '📑',
    category: 'document',
  },
  summarize_document: {
    name: '요약 생성',
    runningMessage: '문서를 요약하고 있습니다',
    icon: '📝',
    category: 'document',
  },
  // External API Tools
  fetch_court_api: {
    name: '대법원 판례 API',
    runningMessage: '대법원에서 판례를 조회하고 있습니다',
    icon: '🏛️',
    category: 'external',
  },
  fetch_statute_api: {
    name: '법령 API',
    runningMessage: '법령 정보를 조회하고 있습니다',
    icon: '📜',
    category: 'external',
  },
  // Workflow Tools
  rag_workflow: {
    name: '법률 정보 검색',
    runningMessage: '법률 정보를 검색하고 있습니다',
    icon: '🔍',
    category: 'search',
  },
  search_legal: {
    name: '법률 검색',
    runningMessage: '법률 정보를 검색하고 있습니다',
    icon: '🔍',
    category: 'search',
  },
  get_user_cases: {
    name: '사건 목록 조회',
    runningMessage: '사용자 사건 목록을 조회하고 있습니다',
    icon: '📋',
    category: 'utility',
  },
  get_case_detail: {
    name: '사건 상세 조회',
    runningMessage: '사건 상세 정보를 조회하고 있습니다',
    icon: '📄',
    category: 'utility',
  },
  document_workflow: {
    name: '문서 분석',
    runningMessage: '문서를 분석하고 있습니다',
    icon: '📄',
    category: 'document',
  },
  case_workflow: {
    name: '판례 분석',
    runningMessage: '판례를 분석하고 있습니다',
    icon: '⚖️',
    category: 'analysis',
  },
  risk_workflow: {
    name: '리스크 평가',
    runningMessage: '리스크를 평가하고 있습니다',
    icon: '📊',
    category: 'analysis',
  },
};

/**
 * 카테고리별 색상 클래스
 */
const CATEGORY_COLORS: Record<string, string> = {
  search: 'inline-tool--search',
  analysis: 'inline-tool--analysis',
  document: 'inline-tool--document',
  external: 'inline-tool--external',
  utility: 'inline-tool--utility',
};

/**
 * 상태별 색상 클래스
 */
const STATUS_COLORS: Record<ToolExecutionStatus, string> = {
  pending: 'inline-tool--pending',
  running: 'inline-tool--running',
  completed: 'inline-tool--completed',
  failed: 'inline-tool--failed',
};

export const InlineToolIndicator: React.FC<InlineToolIndicatorProps> = ({
  executions,
  className,
  showCompleted = true,
  maxVisible = 5,
}) => {
  // 중복 제거 및 최신 상태 유지
  const uniqueExecutions = useMemo(() => {
    const map = new Map<string, ToolExecutionEvent>();
    const statusPriority: Record<ToolExecutionStatus, number> = {
      pending: 0,
      running: 1,
      completed: 2,
      failed: 2,
    };

    executions.forEach(exec => {
      const key = `${exec.step}-${exec.tool}`;
      const existing = map.get(key);
      if (!existing || statusPriority[exec.status] >= statusPriority[existing.status]) {
        map.set(key, exec);
      }
    });

    let result = Array.from(map.values());

    // 완료된 항목 필터링 (옵션)
    if (!showCompleted) {
      result = result.filter(e => e.status !== 'completed');
    }

    return result.slice(-maxVisible);
  }, [executions, showCompleted, maxVisible]);

  // 현재 실행 중인 도구
  const runningTools = uniqueExecutions.filter(e => e.status === 'running');

  // 완료된 도구
  const completedTools = uniqueExecutions.filter(e => e.status === 'completed');

  if (uniqueExecutions.length === 0) {
    return null;
  }

  return (
    <div className={cn('inline-tool-indicator', className)}>
      {/* 실행 중인 도구들 */}
      {runningTools.map((exec, idx) => (
        <ToolItem key={`running-${exec.step}-${exec.tool}-${idx}`} execution={exec} />
      ))}

      {/* 완료된 도구들 (접힘 가능) */}
      {showCompleted && completedTools.length > 0 && (
        <CompletedToolsSummary tools={completedTools} />
      )}

      <style>{styles}</style>
    </div>
  );
};

/**
 * 개별 도구 아이템
 */
const ToolItem: React.FC<{ execution: ToolExecutionEvent }> = ({ execution }) => {
  const config = TOOL_DISPLAY_CONFIG[execution.tool] || {
    name: execution.tool.replace(/_/g, ' '),
    runningMessage: `${execution.tool.replace(/_/g, ' ')} 실행 중`,
    icon: '🔧',
    category: 'utility',
  };

  const categoryColor = CATEGORY_COLORS[config.category] || CATEGORY_COLORS.utility;
  const statusColor = STATUS_COLORS[execution.status];

  const getMessage = () => {
    switch (execution.status) {
      case 'running':
        return config.runningMessage + '...';
      case 'completed':
        return `${config.name} 완료`;
      case 'failed':
        return `${config.name} 실패`;
      case 'pending':
        return `${config.name} 대기 중`;
      default:
        return config.name;
    }
  };

  return (
    <div className={cn('inline-tool-item', categoryColor, statusColor)}>
      <span className="inline-tool-item__icon">
        {execution.status === 'running' ? (
          <span className="inline-tool-item__spinner">{config.icon}</span>
        ) : execution.status === 'completed' ? (
          <CheckIcon />
        ) : execution.status === 'failed' ? (
          <FailedIcon />
        ) : (
          config.icon
        )}
      </span>
      <span className="inline-tool-item__message">{getMessage()}</span>
      {execution.status === 'running' && (
        <span className="inline-tool-item__dots">
          <span className="dot" />
          <span className="dot" />
          <span className="dot" />
        </span>
      )}
      {execution.execution_time !== undefined && execution.status === 'completed' && (
        <span className="inline-tool-item__time">
          {execution.execution_time.toFixed(1)}초
        </span>
      )}
    </div>
  );
};

/**
 * 완료된 도구들 요약
 */
const CompletedToolsSummary: React.FC<{ tools: ToolExecutionEvent[] }> = ({ tools }) => {
  const [isExpanded, setIsExpanded] = React.useState(false);

  if (tools.length === 0) return null;

  // 접힌 상태에서는 간단한 요약만 표시
  if (!isExpanded && tools.length <= 2) {
    return (
      <>
        {tools.map((exec, idx) => (
          <ToolItem key={`completed-${exec.step}-${exec.tool}-${idx}`} execution={exec} />
        ))}
      </>
    );
  }

  return (
    <div className="inline-tool-completed-group">
      {isExpanded ? (
        <>
          {tools.map((exec, idx) => (
            <ToolItem key={`completed-${exec.step}-${exec.tool}-${idx}`} execution={exec} />
          ))}
          <button
            className="inline-tool-toggle"
            onClick={() => setIsExpanded(false)}
          >
            접기
          </button>
        </>
      ) : (
        <button
          className="inline-tool-summary"
          onClick={() => setIsExpanded(true)}
        >
          <CheckIcon />
          <span>{tools.length}개 도구 실행 완료</span>
          <ChevronIcon direction="down" />
        </button>
      )}
    </div>
  );
};

// Icons
function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function FailedIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M15 9l-6 6M9 9l6 6" strokeLinecap="round" />
    </svg>
  );
}

function ChevronIcon({ direction }: { direction: 'up' | 'down' }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      style={{ transform: direction === 'up' ? 'rotate(180deg)' : 'none' }}
    >
      <polyline points="6 9 12 15 18 9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Styles
const styles = `
  .inline-tool-indicator {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 12px;
  }

  .inline-tool-item {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    transition: all 0.2s ease;
  }

  .inline-tool-item__icon {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    min-width: 18px;
  }

  .inline-tool-item__spinner {
    display: inline-block;
    animation: tool-pulse 1.5s ease-in-out infinite;
  }

  .inline-tool-item__message {
    color: var(--text-secondary);
    font-weight: 500;
  }

  .inline-tool-item__time {
    margin-left: auto;
    font-size: 11px;
    color: var(--text-tertiary);
  }

  .inline-tool-item__dots {
    display: flex;
    gap: 3px;
    margin-left: 4px;
  }

  .inline-tool-item__dots .dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--text-tertiary);
    animation: tool-dot-bounce 1.4s ease-in-out infinite;
  }

  .inline-tool-item__dots .dot:nth-child(1) { animation-delay: 0s; }
  .inline-tool-item__dots .dot:nth-child(2) { animation-delay: 0.2s; }
  .inline-tool-item__dots .dot:nth-child(3) { animation-delay: 0.4s; }

  /* Status Colors */
  .inline-tool--running {
    background: linear-gradient(135deg, var(--primary-50) 0%, var(--bg-secondary) 100%);
    border-color: var(--primary-200);
  }

  .inline-tool--running .inline-tool-item__message {
    color: var(--primary-700);
  }

  .inline-tool--completed {
    background: var(--bg-secondary);
    border-color: var(--border-color);
    opacity: 0.8;
  }

  .inline-tool--completed .inline-tool-item__icon {
    color: var(--success-500, #10b981);
  }

  .inline-tool--failed {
    background: var(--error-50, #fef2f2);
    border-color: var(--error-200, #fecaca);
  }

  .inline-tool--failed .inline-tool-item__icon {
    color: var(--error-500, #ef4444);
  }

  .inline-tool--failed .inline-tool-item__message {
    color: var(--error-700, #b91c1c);
  }

  /* Category Colors (subtle accents) */
  .inline-tool--search .inline-tool-item__icon {
    color: var(--primary-500);
  }

  .inline-tool--analysis .inline-tool-item__icon {
    color: var(--warning-500, #f59e0b);
  }

  .inline-tool--document .inline-tool-item__icon {
    color: var(--info-500, #3b82f6);
  }

  .inline-tool--external .inline-tool-item__icon {
    color: var(--purple-500, #8b5cf6);
  }

  /* Completed Group */
  .inline-tool-completed-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .inline-tool-summary {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
    color: var(--text-tertiary);
    background: var(--bg-tertiary);
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .inline-tool-summary:hover {
    background: var(--bg-secondary);
    color: var(--text-secondary);
  }

  .inline-tool-summary svg {
    color: var(--success-500, #10b981);
  }

  .inline-tool-toggle {
    align-self: flex-start;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    color: var(--text-tertiary);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .inline-tool-toggle:hover {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
  }

  /* Animations */
  @keyframes tool-pulse {
    0%, 100% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.1);
      opacity: 0.8;
    }
  }

  @keyframes tool-dot-bounce {
    0%, 80%, 100% {
      transform: translateY(0);
      opacity: 0.4;
    }
    40% {
      transform: translateY(-4px);
      opacity: 1;
    }
  }

  /* Dark mode adjustments */
  @media (prefers-color-scheme: dark) {
    .inline-tool--running {
      background: linear-gradient(135deg, rgba(var(--primary-rgb), 0.15) 0%, var(--bg-secondary) 100%);
    }

    .inline-tool--running .inline-tool-item__message {
      color: var(--primary-300);
    }

    .inline-tool--failed {
      background: rgba(239, 68, 68, 0.1);
    }
  }
`;

export default InlineToolIndicator;
