/**
 * Agent Hub - Progress Indicator Component
 *
 * AI 처리 진행 상태를 시각적으로 표시하는 컴포넌트
 * - 단계별 아이콘
 * - 진행률 바
 * - 현재 처리 단계 메시지
 */

import React, { useMemo } from 'react';
import { cn } from '../../../lib/utils';
import type { ProgressEvent, ToolExecutionEvent } from '../../../services/agentHubService';
import { ToolExecutionLog } from './ToolExecutionLog';

interface ProgressIndicatorProps {
  progress: ProgressEvent;
  className?: string;
  showPercentage?: boolean;
  compact?: boolean;
  toolExecutions?: ToolExecutionEvent[];
}

/**
 * 단계별 아이콘 및 색상 설정
 */
const STEP_CONFIG: Record<ProgressEvent['step'], {
  icon: React.ReactNode;
  color: string;
  label: string;
}> = {
  ANALYZING: {
    icon: <AnalyzeIcon />,
    color: 'text-blue-500',
    label: '분석 중',
  },
  PLANNING: {
    icon: <PlanIcon />,
    color: 'text-purple-500',
    label: '계획 수립',
  },
  SEARCHING: {
    icon: <SearchIcon />,
    color: 'text-green-500',
    label: '검색 중',
  },
  EXECUTING: {
    icon: <ExecuteIcon />,
    color: 'text-orange-500',
    label: '실행 중',
  },
  THINKING: {
    icon: <ThinkIcon />,
    color: 'text-indigo-500',
    label: '추론 중',
  },
  GENERATING: {
    icon: <GenerateIcon />,
    color: 'text-pink-500',
    label: '생성 중',
  },
  COMPLETED: {
    icon: <CheckIcon />,
    color: 'text-emerald-500',
    label: '완료',
  },
};

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  progress,
  className,
  showPercentage = true,
  compact = false,
  toolExecutions = [],
}) => {
  const config = useMemo(() =>
    STEP_CONFIG[progress.step] || STEP_CONFIG.EXECUTING,
    [progress.step]
  );

  const progressBarStyle = useMemo(() => ({
    width: `${Math.min(progress.percentage, 100)}%`,
    transition: 'width 0.3s ease-out',
  }), [progress.percentage]);

  // compact 모드용 도구 정보 추출
  const compactToolInfo = useMemo(() => {
    if (!progress.step_details) return null;
    const { workflow, tool, current_workflow, current_tool } = progress.step_details;
    const activeItem = current_workflow || workflow || current_tool || tool;
    if (!activeItem) return null;
    const info = TOOL_DISPLAY_NAMES[activeItem];
    return info ? `${info.icon} ${info.label}` : null;
  }, [progress.step_details]);

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2 flex-wrap', className)}>
        <div className={cn('animate-spin-slow', config.color)}>
          {config.icon}
        </div>
        <span className="text-sm text-[var(--text-secondary)]">
          {progress.message}
        </span>
        {compactToolInfo && (
          <span className="text-xs text-[var(--text-tertiary)] px-1.5 py-0.5 bg-[var(--bg-tertiary)] rounded">
            {compactToolInfo}
          </span>
        )}
        {showPercentage && (
          <span className="text-xs text-[var(--text-tertiary)] ml-auto">
            {progress.percentage}%
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={cn('progress-indicator', className)}>
      {/* Header: Icon + Step Label + Percentage */}
      <div className="progress-indicator__header">
        <div className="progress-indicator__step">
          <div className={cn(
            'progress-indicator__icon',
            config.color,
            progress.step !== 'COMPLETED' && 'animate-pulse'
          )}>
            {config.icon}
          </div>
          <span className="progress-indicator__label">
            {config.label}
          </span>
        </div>
        {showPercentage && (
          <span className="progress-indicator__percentage">
            {progress.percentage}%
          </span>
        )}
      </div>

      {/* Progress Bar */}
      <div className="progress-indicator__bar-wrapper">
        <div
          className="progress-indicator__bar"
          style={progressBarStyle}
        />
      </div>

      {/* Message */}
      <div className="progress-indicator__message">
        {progress.message}
      </div>

      {/* Execution Path Badge (optional) */}
      {progress.execution_path && (
        <div className="progress-indicator__path">
          <PathBadge path={progress.execution_path} />
        </div>
      )}

      {/* Step Details (workflow/tool info) */}
      {progress.step_details && (
        <StepDetailsDisplay details={progress.step_details} />
      )}

      {/* Tool Execution Log (Phase 7) */}
      {toolExecutions.length > 0 && (
        <ToolExecutionLog
          executions={toolExecutions}
          compact={false}
          maxVisible={5}
        />
      )}

      <style>{`
        .progress-indicator {
          padding: 12px 16px;
          background: var(--bg-secondary);
          border-radius: 12px;
          border: 1px solid var(--border-color);
        }

        .progress-indicator__header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 8px;
        }

        .progress-indicator__step {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .progress-indicator__icon {
          width: 20px;
          height: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .progress-indicator__icon svg {
          width: 18px;
          height: 18px;
        }

        .progress-indicator__label {
          font-size: 14px;
          font-weight: 500;
          color: var(--text-primary);
        }

        .progress-indicator__percentage {
          font-size: 12px;
          font-weight: 600;
          color: var(--text-secondary);
          font-variant-numeric: tabular-nums;
        }

        .progress-indicator__bar-wrapper {
          height: 4px;
          background: var(--bg-tertiary);
          border-radius: 2px;
          overflow: hidden;
          margin-bottom: 8px;
        }

        .progress-indicator__bar {
          height: 100%;
          background: linear-gradient(90deg,
            var(--primary-500) 0%,
            var(--primary-400) 100%
          );
          border-radius: 2px;
        }

        .progress-indicator__message {
          font-size: 13px;
          color: var(--text-secondary);
          line-height: 1.4;
        }

        .progress-indicator__path {
          margin-top: 8px;
        }

        @keyframes spin-slow {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        .animate-spin-slow {
          animation: spin-slow 2s linear infinite;
        }
      `}</style>
    </div>
  );
};

/**
 * Path Badge Component
 */
const PathBadge: React.FC<{ path: ProgressEvent['execution_path'] }> = ({ path }) => {
  const pathConfig: Record<NonNullable<typeof path>, { label: string; color: string }> = {
    fast: { label: '빠른 응답', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
    medium: { label: '표준 처리', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
    deep: { label: '심층 분석', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' },
    thinking: { label: '추론 모드', color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' },
  };

  if (!path) return null;

  const config = pathConfig[path];
  if (!config) return null;

  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
      config.color
    )}>
      {config.label}
    </span>
  );
};

/**
 * Tool/Workflow Badge Component
 */
const TOOL_DISPLAY_NAMES: Record<string, { label: string; icon: string }> = {
  // Workflows
  'rag_workflow': { label: '법률 정보 검색', icon: '🔍' },
  'document_workflow': { label: '문서 분석', icon: '📄' },
  'case_workflow': { label: '판례 분석', icon: '⚖️' },
  'risk_workflow': { label: '리스크 평가', icon: '⚠️' },
  'llm_comparison_workflow': { label: '비교 분석', icon: '🔄' },
  // External API Tools
  'fetch_court_api': { label: '대법원 판례 API', icon: '🏛️' },
  'fetch_statute_api': { label: '법령 API', icon: '📜' },
  // Document Tools
  'analyze_document': { label: '문서 분석', icon: '📋' },
  'extract_clauses': { label: '조항 추출', icon: '📑' },
  'summarize_document': { label: '요약 생성', icon: '📝' },
  // Search Tools
  'search_precedents': { label: '판례 검색', icon: '🔎' },
  'search_statutes': { label: '법령 검색', icon: '📚' },
  'search_related_cases': { label: '관련 사건 검색', icon: '🔗' },
  // Analysis Tools
  'analyze_risks': { label: '리스크 분석', icon: '📊' },
  'compare_documents': { label: '문서 비교', icon: '⚖️' },
};

const ToolBadge: React.FC<{ toolName: string; type: 'workflow' | 'tool' }> = ({ toolName, type }) => {
  const displayInfo = TOOL_DISPLAY_NAMES[toolName] || {
    label: toolName.replace(/_/g, ' '),
    icon: type === 'workflow' ? '⚙️' : '🔧'
  };

  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium',
      type === 'workflow'
        ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400'
        : 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400'
    )}>
      <span>{displayInfo.icon}</span>
      <span>{displayInfo.label}</span>
    </span>
  );
};

/**
 * Step Details Display Component
 */
const StepDetailsDisplay: React.FC<{ details: Record<string, any> }> = ({ details }) => {
  if (!details || Object.keys(details).length === 0) return null;

  const { workflow, tool, tasks, total_steps, current_tool, current_workflow } = details;

  // 표시할 내용이 없으면 렌더링하지 않음
  const activeWorkflow = current_workflow || workflow;
  const activeTool = current_tool || tool;
  const hasActiveTasks = tasks && Array.isArray(tasks) && tasks.length > 0;

  if (!activeWorkflow && !activeTool && !hasActiveTasks) return null;

  return (
    <div className="progress-indicator__details">
      {/* Active Workflow */}
      {activeWorkflow && (
        <div className="progress-indicator__detail-row">
          <span className="progress-indicator__detail-label">워크플로우:</span>
          <ToolBadge toolName={activeWorkflow} type="workflow" />
        </div>
      )}

      {/* Active Tool */}
      {activeTool && (
        <div className="progress-indicator__detail-row">
          <span className="progress-indicator__detail-label">도구:</span>
          <ToolBadge toolName={activeTool} type="tool" />
        </div>
      )}

      {/* Parallel Tasks (for deep path) */}
      {hasActiveTasks && (
        <div className="progress-indicator__detail-row progress-indicator__detail-row--wrap">
          <span className="progress-indicator__detail-label">실행 중:</span>
          <div className="progress-indicator__tasks">
            {tasks.slice(0, 3).map((task: string, idx: number) => (
              <ToolBadge key={idx} toolName={task} type="workflow" />
            ))}
            {tasks.length > 3 && (
              <span className="text-xs text-[var(--text-tertiary)]">
                +{tasks.length - 3}개
              </span>
            )}
          </div>
        </div>
      )}

      {/* Total Steps (for deep path) */}
      {total_steps && (
        <div className="progress-indicator__detail-row">
          <span className="progress-indicator__detail-label">단계:</span>
          <span className="text-xs text-[var(--text-secondary)]">
            총 {total_steps}단계
          </span>
        </div>
      )}

      <style>{`
        .progress-indicator__details {
          margin-top: 8px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .progress-indicator__detail-row {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .progress-indicator__detail-row--wrap {
          flex-wrap: wrap;
        }

        .progress-indicator__detail-label {
          font-size: 11px;
          color: var(--text-tertiary);
          min-width: 60px;
        }

        .progress-indicator__tasks {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }
      `}</style>
    </div>
  );
};

// Icons
function AnalyzeIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
    </svg>
  );
}

function PlanIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  );
}

function ExecuteIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  );
}

function ThinkIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
  );
}

function GenerateIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

export default ProgressIndicator;
