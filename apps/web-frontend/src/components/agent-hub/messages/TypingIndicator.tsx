/**
 * Agent Hub - Typing Indicator Component
 *
 * AI가 응답을 생성 중일 때 표시하는 점 3개 애니메이션
 */

import React from 'react';
import { cn } from '../../../lib/utils';

interface TypingIndicatorProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  className,
  size = 'md',
  label,
}) => {
  const sizeClasses = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5',
  };

  const gapClasses = {
    sm: 'gap-1',
    md: 'gap-1.5',
    lg: 'gap-2',
  };

  return (
    <div className={cn('flex items-center', gapClasses[size], className)}>
      <div className={cn('flex items-center', gapClasses[size])}>
        {[0, 1, 2].map((index) => (
          <span
            key={index}
            className={cn(
              sizeClasses[size],
              'rounded-full',
              'bg-[var(--text-tertiary)]',
              'animate-bounce'
            )}
            style={{
              animationDelay: `${index * 0.15}s`,
              animationDuration: '0.6s',
            }}
          />
        ))}
      </div>
      {label && (
        <span className="ml-2 text-sm text-[var(--text-tertiary)]">{label}</span>
      )}
    </div>
  );
};

/**
 * Pulse Typing Indicator - 다른 스타일의 타이핑 인디케이터
 */
export const PulseTypingIndicator: React.FC<TypingIndicatorProps> = ({
  className,
  size = 'md',
  label,
}) => {
  const sizeClasses = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5',
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex items-center gap-1.5">
        {[0, 1, 2].map((index) => (
          <span
            key={index}
            className={cn(
              sizeClasses[size],
              'rounded-full',
              'bg-primary-500'
            )}
            style={{
              animation: 'pulse-dot 1.4s ease-in-out infinite',
              animationDelay: `${index * 0.2}s`,
            }}
          />
        ))}
      </div>
      {label && (
        <span className="text-sm text-[var(--text-tertiary)]">{label}</span>
      )}
      <style>{`
        @keyframes pulse-dot {
          0%, 60%, 100% {
            transform: scale(1);
            opacity: 0.6;
          }
          30% {
            transform: scale(1.3);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
};

/**
 * Wave Typing Indicator - 파도 스타일의 타이핑 인디케이터
 */
export const WaveTypingIndicator: React.FC<TypingIndicatorProps> = ({
  className,
  size = 'md',
  label,
}) => {
  const sizeClasses = {
    sm: 'w-1 h-3',
    md: 'w-1.5 h-4',
    lg: 'w-2 h-5',
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex items-end gap-0.5">
        {[0, 1, 2, 3].map((index) => (
          <span
            key={index}
            className={cn(
              sizeClasses[size],
              'rounded-full',
              'bg-primary-500'
            )}
            style={{
              animation: 'wave 1.2s ease-in-out infinite',
              animationDelay: `${index * 0.1}s`,
            }}
          />
        ))}
      </div>
      {label && (
        <span className="text-sm text-[var(--text-tertiary)]">{label}</span>
      )}
      <style>{`
        @keyframes wave {
          0%, 100% {
            transform: scaleY(0.5);
            opacity: 0.5;
          }
          50% {
            transform: scaleY(1);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
};

/**
 * Thinking Indicator - AI가 생각 중임을 표시
 */
export const ThinkingIndicator: React.FC<{ className?: string }> = ({ className }) => {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div className="relative">
        <div
          className={cn(
            'w-8 h-8 rounded-full',
            'border-2 border-primary-500/30',
            'border-t-primary-500',
            'animate-spin'
          )}
        />
        <div
          className={cn(
            'absolute inset-1',
            'w-6 h-6 rounded-full',
            'bg-gradient-to-br from-primary-400 to-primary-600',
            'flex items-center justify-center'
          )}
        >
          <BrainIcon className="w-3.5 h-3.5 text-white" />
        </div>
      </div>
      <div className="flex flex-col">
        <span className="text-sm font-medium text-[var(--text-primary)]">
          분석 중...
        </span>
        <span className="text-xs text-[var(--text-tertiary)]">
          잠시만 기다려주세요
        </span>
      </div>
    </div>
  );
};

// Brain Icon
const BrainIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
    />
  </svg>
);

export default TypingIndicator;
