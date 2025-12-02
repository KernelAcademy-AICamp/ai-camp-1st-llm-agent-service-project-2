/**
 * Agent Hub - Context Panel Component
 *
 * 실행 상태 표시, 추천 질문, 대화 요약
 */

import React, { useState } from 'react';
import { cn } from '../../../lib/utils';

interface ExecutionStatus {
  status: 'idle' | 'running' | 'completed' | 'error';
  currentStep?: string;
  progress?: number;
  workflows?: string[];
}

interface SuggestedQuestion {
  id: string;
  text: string;
  category: string;
}

interface ConversationSummary {
  topics: string[];
  keyPoints: string[];
  relatedCases?: string[];
}

interface ContextPanelProps {
  executionStatus?: ExecutionStatus;
  suggestedQuestions?: SuggestedQuestion[];
  conversationSummary?: ConversationSummary;
  onQuestionClick?: (question: string) => void;
  className?: string;
}

// Mock data
const mockSuggestedQuestions: SuggestedQuestion[] = [
  { id: '1', text: '이 계약서의 해지 조건은 무엇인가요?', category: '계약' },
  { id: '2', text: '관련 판례를 찾아줄 수 있나요?', category: '판례' },
  { id: '3', text: '위약금 조항은 유효한가요?', category: '계약' },
  { id: '4', text: '갱신권 행사 기한은 언제까지인가요?', category: '임대차' },
];

const mockSummary: ConversationSummary = {
  topics: ['임대차 계약', '특약조항', '보증금 반환'],
  keyPoints: [
    '2년 계약, 자동갱신 조항 포함',
    '보증금 5천만원, 월세 150만원',
    '반려동물 허용 특약 확인 필요',
  ],
  relatedCases: ['대법원 2023다12345', '서울고등법원 2022나67890'],
};

export const ContextPanel: React.FC<ContextPanelProps> = ({
  executionStatus = { status: 'idle' },
  suggestedQuestions = mockSuggestedQuestions,
  conversationSummary = mockSummary,
  onQuestionClick,
  className,
}) => {
  const [expandedSection, setExpandedSection] = useState<string | null>('suggestions');

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  return (
    <div className={cn('h-full flex flex-col', className)}>
      {/* Panel Header */}
      <div className="p-4 border-b border-[var(--border-primary)]">
        <h2 className="font-semibold text-[var(--text-primary)]">컨텍스트</h2>
        <p className="text-xs text-[var(--text-tertiary)] mt-0.5">
          실행 상태 및 추천 질문
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {/* Execution Status Section */}
        <Section
          title="실행 상태"
          icon={<StatusIcon className="w-4 h-4" />}
          isExpanded={expandedSection === 'status'}
          onToggle={() => toggleSection('status')}
        >
          <ExecutionStatusCard status={executionStatus} />
        </Section>

        {/* Suggested Questions Section */}
        <Section
          title="추천 질문"
          icon={<LightbulbIcon className="w-4 h-4" />}
          isExpanded={expandedSection === 'suggestions'}
          onToggle={() => toggleSection('suggestions')}
          badge={suggestedQuestions.length}
        >
          <div className="space-y-2">
            {suggestedQuestions.map((q) => (
              <button
                key={q.id}
                onClick={() => onQuestionClick?.(q.text)}
                className={cn(
                  'w-full text-left',
                  'px-3 py-2.5',
                  'rounded-lg',
                  'bg-[var(--bg-tertiary)]',
                  'hover:bg-[var(--border-primary)]',
                  'border border-transparent',
                  'hover:border-[var(--border-secondary)]',
                  'transition-all duration-200',
                  'group'
                )}
              >
                <div className="flex items-start gap-2">
                  <QuestionIcon className="w-4 h-4 mt-0.5 text-primary-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[var(--text-primary)] group-hover:text-primary-600">
                      {q.text}
                    </p>
                    <span className="text-xs text-[var(--text-tertiary)] mt-1">
                      {q.category}
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </Section>

        {/* Conversation Summary Section */}
        <Section
          title="대화 요약"
          icon={<SummaryIcon className="w-4 h-4" />}
          isExpanded={expandedSection === 'summary'}
          onToggle={() => toggleSection('summary')}
        >
          <div className="space-y-4">
            {/* Topics */}
            <div>
              <h4 className="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-2">
                주요 주제
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {conversationSummary.topics.map((topic, idx) => (
                  <span
                    key={idx}
                    className={cn(
                      'px-2.5 py-1',
                      'text-xs font-medium',
                      'rounded-full',
                      'bg-primary-500/10 text-primary-600',
                      'border border-primary-500/20'
                    )}
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>

            {/* Key Points */}
            <div>
              <h4 className="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-2">
                핵심 포인트
              </h4>
              <ul className="space-y-2">
                {conversationSummary.keyPoints.map((point, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <CheckIcon className="w-4 h-4 text-[var(--color-success-500)] flex-shrink-0 mt-0.5" />
                    <span className="text-sm text-[var(--text-secondary)]">{point}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Related Cases */}
            {conversationSummary.relatedCases && conversationSummary.relatedCases.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-2">
                  관련 판례
                </h4>
                <div className="space-y-1.5">
                  {conversationSummary.relatedCases.map((caseNum, idx) => (
                    <a
                      key={idx}
                      href={`/research/cases/${caseNum}`}
                      className={cn(
                        'flex items-center gap-2',
                        'px-3 py-2',
                        'rounded-lg',
                        'bg-[var(--bg-tertiary)]',
                        'hover:bg-[var(--border-primary)]',
                        'text-sm text-[var(--text-primary)]',
                        'transition-colors duration-200'
                      )}
                    >
                      <BookIcon className="w-4 h-4 text-[var(--text-tertiary)]" />
                      {caseNum}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Section>
      </div>

      {/* Panel Footer */}
      <div className="p-4 border-t border-[var(--border-primary)]">
        <button
          className={cn(
            'w-full flex items-center justify-center gap-2',
            'px-4 py-2',
            'text-sm text-[var(--text-secondary)]',
            'rounded-lg',
            'border border-[var(--border-primary)]',
            'hover:bg-[var(--bg-tertiary)]',
            'transition-colors duration-200'
          )}
        >
          <ExportIcon className="w-4 h-4" />
          대화 내보내기
        </button>
      </div>
    </div>
  );
};

// Section Component
interface SectionProps {
  title: string;
  icon: React.ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
  badge?: number;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({
  title,
  icon,
  isExpanded,
  onToggle,
  badge,
  children,
}) => {
  return (
    <div className="border-b border-[var(--border-primary)]">
      <button
        onClick={onToggle}
        className={cn(
          'w-full flex items-center justify-between',
          'px-4 py-3',
          'hover:bg-[var(--bg-tertiary)]',
          'transition-colors duration-200'
        )}
      >
        <div className="flex items-center gap-2">
          <span className="text-[var(--text-tertiary)]">{icon}</span>
          <span className="text-sm font-medium text-[var(--text-primary)]">{title}</span>
          {badge !== undefined && badge > 0 && (
            <span
              className={cn(
                'px-1.5 py-0.5',
                'text-xs font-medium',
                'rounded-full',
                'bg-primary-500 text-white'
              )}
            >
              {badge}
            </span>
          )}
        </div>
        <ChevronIcon
          className={cn(
            'w-4 h-4 text-[var(--text-tertiary)]',
            'transition-transform duration-200',
            isExpanded && 'rotate-180'
          )}
        />
      </button>
      {isExpanded && (
        <div className="px-4 pb-4 animate-fade-in-up">
          {children}
        </div>
      )}
    </div>
  );
};

// Execution Status Card
const ExecutionStatusCard: React.FC<{ status: ExecutionStatus }> = ({ status }) => {
  const statusConfig = {
    idle: { label: '대기 중', color: 'var(--text-tertiary)', bgColor: 'var(--bg-tertiary)' },
    running: { label: '실행 중', color: 'var(--color-primary-500)', bgColor: 'var(--color-primary-50)' },
    completed: { label: '완료', color: 'var(--color-success-500)', bgColor: 'var(--color-success-50)' },
    error: { label: '오류', color: 'var(--color-error-500)', bgColor: 'var(--color-error-50)' },
  };

  const config = statusConfig[status.status];

  return (
    <div
      className={cn(
        'p-4 rounded-xl',
        'border border-[var(--border-primary)]'
      )}
      style={{ backgroundColor: config.bgColor }}
    >
      <div className="flex items-center gap-2 mb-3">
        <div
          className={cn(
            'w-2.5 h-2.5 rounded-full',
            status.status === 'running' && 'animate-pulse'
          )}
          style={{ backgroundColor: config.color }}
        />
        <span className="text-sm font-medium" style={{ color: config.color }}>
          {config.label}
        </span>
      </div>

      {status.status === 'running' && (
        <>
          {status.currentStep && (
            <p className="text-sm text-[var(--text-secondary)] mb-2">
              {status.currentStep}
            </p>
          )}
          {status.progress !== undefined && (
            <div className="w-full h-1.5 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${status.progress}%`,
                  backgroundColor: config.color,
                }}
              />
            </div>
          )}
          {status.workflows && status.workflows.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {status.workflows.map((workflow, idx) => (
                <span
                  key={idx}
                  className={cn(
                    'px-2 py-0.5',
                    'text-xs',
                    'rounded',
                    'bg-[var(--bg-secondary)]',
                    'text-[var(--text-secondary)]'
                  )}
                >
                  {workflow}
                </span>
              ))}
            </div>
          )}
        </>
      )}

      {status.status === 'idle' && (
        <p className="text-sm text-[var(--text-tertiary)]">
          질문을 입력하면 분석을 시작합니다
        </p>
      )}
    </div>
  );
};

// Icons - 인라인 스타일로 크기 고정
const StatusIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const LightbulbIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
  </svg>
);

const SummaryIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const QuestionIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const CheckIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const BookIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
  </svg>
);

const ChevronIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const ExportIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
  </svg>
);

export default ContextPanel;
