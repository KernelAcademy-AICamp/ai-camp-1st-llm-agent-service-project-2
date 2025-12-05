/**
 * Agent Hub - Tool Execution Log Component
 *
 * LLM이 사용하는 도구의 실행 상태를 실시간으로 표시하는 컴포넌트
 * - 도구 선택 이유
 * - 입력값 미리보기
 * - 실행 상태 (대기 → 실행 중 → 완료/실패)
 * - 실행 시간
 * - 결과 미리보기
 */

import React, { useMemo } from 'react';
import { cn } from '../../../lib/utils';
import type { ToolExecutionEvent, ToolExecutionStatus } from '../../../services/agentHubService';

interface ToolExecutionLogProps {
  executions: ToolExecutionEvent[];
  className?: string;
  compact?: boolean;
  maxVisible?: number;
}

/**
 * 카테고리별 아이콘 매핑
 */
const CATEGORY_ICONS: Record<string, string> = {
  search: '🔍',
  analysis: '📊',
  document: '📄',
  external: '🌐',
  utility: '🔧',
  unknown: '⚙️',
};

/**
 * 도구 이름 → 친화적 이름 매핑
 */
const TOOL_DISPLAY_NAMES: Record<string, string> = {
  // Search Tools
  search_precedents: '판례 검색',
  search_statutes: '법령 검색',
  search_related_cases: '관련 사건 검색',
  rag_search: 'RAG 검색',
  semantic_search: '시맨틱 검색',
  // Analysis Tools
  analyze_risks: '리스크 분석',
  analyze_document: '문서 분석',
  compare_documents: '문서 비교',
  extract_clauses: '조항 추출',
  summarize_document: '요약 생성',
  // External API Tools
  fetch_court_api: '대법원 판례 API',
  fetch_statute_api: '법령 API',
  // Workflow Tools
  rag_workflow: '법률 정보 검색',
  document_workflow: '문서 분석',
  case_workflow: '판례 분석',
  risk_workflow: '리스크 평가',
};

/**
 * 상태별 스타일 설정
 */
const STATUS_CONFIG: Record<ToolExecutionStatus, {
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  label: string;
}> = {
  pending: {
    icon: <PendingIcon />,
    color: 'text-gray-400',
    bgColor: 'bg-gray-100 dark:bg-gray-800',
    label: '대기',
  },
  running: {
    icon: <RunningIcon />,
    color: 'text-blue-500',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    label: '실행 중',
  },
  completed: {
    icon: <CompletedIcon />,
    color: 'text-green-500',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
    label: '완료',
  },
  failed: {
    icon: <FailedIcon />,
    color: 'text-red-500',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    label: '실패',
  },
};

export const ToolExecutionLog: React.FC<ToolExecutionLogProps> = ({
  executions,
  className,
  compact = false,
  maxVisible = 5,
}) => {
  // 중복 제거 및 최신 상태 유지 (같은 step + tool 조합)
  const uniqueExecutions = useMemo(() => {
    const map = new Map<string, ToolExecutionEvent>();
    executions.forEach(exec => {
      const key = `${exec.step}-${exec.tool}`;
      const existing = map.get(key);
      // 더 최신 상태로 업데이트 (completed/failed > running > pending)
      const statusPriority: Record<ToolExecutionStatus, number> = {
        pending: 0,
        running: 1,
        completed: 2,
        failed: 2,
      };
      if (!existing || statusPriority[exec.status] >= statusPriority[existing.status]) {
        map.set(key, exec);
      }
    });
    return Array.from(map.values()).slice(-maxVisible);
  }, [executions, maxVisible]);

  if (uniqueExecutions.length === 0) {
    return null;
  }

  if (compact) {
    return (
      <div className={cn('tool-execution-log--compact', className)}>
        {uniqueExecutions.map((exec, idx) => (
          <CompactToolItem key={`${exec.step}-${exec.tool}-${idx}`} execution={exec} />
        ))}
        <style>{compactStyles}</style>
      </div>
    );
  }

  return (
    <div className={cn('tool-execution-log', className)}>
      <div className="tool-execution-log__header">
        <span className="tool-execution-log__title">🛠️ 도구 실행 로그</span>
        <span className="tool-execution-log__count">
          {uniqueExecutions.filter(e => e.status === 'completed').length}/{uniqueExecutions.length} 완료
        </span>
      </div>
      <div className="tool-execution-log__list">
        {uniqueExecutions.map((exec, idx) => (
          <ToolExecutionItem
            key={`${exec.step}-${exec.tool}-${idx}`}
            execution={exec}
            isLast={idx === uniqueExecutions.length - 1}
          />
        ))}
      </div>
      <style>{styles}</style>
    </div>
  );
};

/**
 * 개별 도구 실행 아이템
 */
const ToolExecutionItem: React.FC<{
  execution: ToolExecutionEvent;
  isLast: boolean;
}> = ({ execution, isLast }) => {
  const statusConfig = STATUS_CONFIG[execution.status];
  const categoryIcon = CATEGORY_ICONS[execution.category] || CATEGORY_ICONS.unknown;
  const toolName = TOOL_DISPLAY_NAMES[execution.tool] || execution.tool.replace(/_/g, ' ');

  return (
    <div className={cn(
      'tool-execution-item',
      !isLast && 'tool-execution-item--with-connector'
    )}>
      {/* Status Icon */}
      <div className={cn('tool-execution-item__status', statusConfig.color)}>
        {execution.status === 'running' ? (
          <div className="animate-spin">{statusConfig.icon}</div>
        ) : (
          statusConfig.icon
        )}
      </div>

      {/* Content */}
      <div className="tool-execution-item__content">
        {/* Tool Name + Category */}
        <div className="tool-execution-item__header">
          <span className="tool-execution-item__category">{categoryIcon}</span>
          <span className="tool-execution-item__name">{toolName}</span>
          {execution.execution_time !== undefined && (
            <span className="tool-execution-item__time">
              {execution.execution_time.toFixed(1)}초
            </span>
          )}
        </div>

        {/* Input Preview */}
        {execution.input_preview && (
          <div className="tool-execution-item__input">
            <span className="tool-execution-item__input-label">입력:</span>
            <span className="tool-execution-item__input-value">
              "{execution.input_preview}"
            </span>
          </div>
        )}

        {/* Reason (from think node) */}
        {execution.reason && execution.status === 'pending' && (
          <div className="tool-execution-item__reason">
            💭 {execution.reason}
          </div>
        )}

        {/* Result Preview */}
        {execution.status === 'completed' && execution.result_preview && (
          <div className="tool-execution-item__result">
            <span className="tool-execution-item__result-label">결과:</span>
            <span className="tool-execution-item__result-value">
              {execution.result_preview}
            </span>
          </div>
        )}

        {/* Error Message */}
        {execution.status === 'failed' && execution.result_preview && (
          <div className="tool-execution-item__error">
            ❌ {execution.result_preview}
          </div>
        )}

        {/* Running Status */}
        {execution.status === 'running' && (
          <div className="tool-execution-item__running">
            <span className="tool-execution-item__running-dot" />
            실행 중...
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * 컴팩트 버전 도구 아이템
 */
const CompactToolItem: React.FC<{ execution: ToolExecutionEvent }> = ({ execution }) => {
  const statusConfig = STATUS_CONFIG[execution.status];
  const toolName = TOOL_DISPLAY_NAMES[execution.tool] || execution.tool.replace(/_/g, ' ');

  return (
    <div className={cn('compact-tool-item', statusConfig.bgColor)}>
      <span className={cn('compact-tool-item__icon', statusConfig.color)}>
        {execution.status === 'running' ? (
          <span className="animate-spin inline-block">{statusConfig.icon}</span>
        ) : (
          statusConfig.icon
        )}
      </span>
      <span className="compact-tool-item__name">{toolName}</span>
      {execution.execution_time !== undefined && (
        <span className="compact-tool-item__time">({execution.execution_time.toFixed(1)}s)</span>
      )}
    </div>
  );
};

// Icons
function PendingIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="8" cy="8" r="6" />
    </svg>
  );
}

function RunningIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="8" cy="8" r="6" strokeDasharray="20" strokeDashoffset="5" />
    </svg>
  );
}

function CompletedIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 8l3 3 7-7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function FailedIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 4l8 8M12 4l-8 8" strokeLinecap="round" />
    </svg>
  );
}

// Styles
const styles = `
  .tool-execution-log {
    padding: 12px;
    background: var(--bg-secondary);
    border-radius: 8px;
    border: 1px solid var(--border-color);
    margin-top: 8px;
  }

  .tool-execution-log__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
  }

  .tool-execution-log__title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .tool-execution-log__count {
    font-size: 11px;
    color: var(--text-tertiary);
    background: var(--bg-tertiary);
    padding: 2px 8px;
    border-radius: 10px;
  }

  .tool-execution-log__list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .tool-execution-item {
    display: flex;
    gap: 10px;
    padding: 8px 0;
    position: relative;
  }

  .tool-execution-item--with-connector::after {
    content: '';
    position: absolute;
    left: 7px;
    top: 28px;
    bottom: -4px;
    width: 2px;
    background: var(--border-color);
  }

  .tool-execution-item__status {
    flex-shrink: 0;
    width: 16px;
    height: 16px;
    margin-top: 2px;
  }

  .tool-execution-item__content {
    flex: 1;
    min-width: 0;
  }

  .tool-execution-item__header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
  }

  .tool-execution-item__category {
    font-size: 14px;
  }

  .tool-execution-item__name {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
  }

  .tool-execution-item__time {
    font-size: 11px;
    color: var(--text-tertiary);
    margin-left: auto;
  }

  .tool-execution-item__input,
  .tool-execution-item__result {
    display: flex;
    align-items: flex-start;
    gap: 4px;
    font-size: 12px;
    margin-top: 2px;
  }

  .tool-execution-item__input-label,
  .tool-execution-item__result-label {
    color: var(--text-tertiary);
    flex-shrink: 0;
  }

  .tool-execution-item__input-value {
    color: var(--text-secondary);
    font-style: italic;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tool-execution-item__result-value {
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .tool-execution-item__reason {
    font-size: 11px;
    color: var(--text-tertiary);
    margin-top: 4px;
    padding: 4px 8px;
    background: var(--bg-tertiary);
    border-radius: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tool-execution-item__error {
    font-size: 12px;
    color: var(--error-color, #ef4444);
    margin-top: 4px;
  }

  .tool-execution-item__running {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--text-tertiary);
    margin-top: 4px;
  }

  .tool-execution-item__running-dot {
    width: 6px;
    height: 6px;
    background: var(--primary-500);
    border-radius: 50%;
    animation: pulse 1.5s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .animate-spin {
    animation: spin 1s linear infinite;
  }
`;

const compactStyles = `
  .tool-execution-log--compact {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
  }

  .compact-tool-item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 12px;
  }

  .compact-tool-item__icon {
    width: 14px;
    height: 14px;
  }

  .compact-tool-item__name {
    color: var(--text-primary);
  }

  .compact-tool-item__time {
    color: var(--text-tertiary);
    font-size: 10px;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .animate-spin {
    animation: spin 1s linear infinite;
  }
`;

export default ToolExecutionLog;
