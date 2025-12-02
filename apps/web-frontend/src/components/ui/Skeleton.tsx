/**
 * UI Component - Skeleton
 *
 * 로딩 스켈레톤 애니메이션 컴포넌트
 * 다양한 형태의 스켈레톤 지원
 */

import React from 'react';
import { cn } from '../../lib/utils';

export interface SkeletonProps {
  className?: string;
  variant?: 'default' | 'circular' | 'rounded' | 'text';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'default',
  width,
  height,
  animation = 'wave',
}) => {
  // Base styles
  const baseStyles = 'bg-[var(--bg-tertiary)]';

  // Variant styles
  const variantStyles = {
    default: 'rounded-lg',
    circular: 'rounded-full',
    rounded: 'rounded-xl',
    text: 'rounded h-4',
  };

  // Animation styles
  const animationStyles = {
    pulse: 'animate-pulse',
    wave: 'animate-skeleton',
    none: '',
  };

  const style: React.CSSProperties = {
    width: width,
    height: height,
  };

  return (
    <div
      className={cn(
        baseStyles,
        variantStyles[variant],
        animationStyles[animation],
        className
      )}
      style={style}
    />
  );
};

/**
 * Skeleton Text - 텍스트 로딩용
 */
interface SkeletonTextProps {
  lines?: number;
  lastLineWidth?: string;
  className?: string;
  lineClassName?: string;
}

export const SkeletonText: React.FC<SkeletonTextProps> = ({
  lines = 3,
  lastLineWidth = '60%',
  className,
  lineClassName,
}) => {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          variant="text"
          className={lineClassName}
          width={index === lines - 1 ? lastLineWidth : '100%'}
        />
      ))}
    </div>
  );
};

/**
 * Skeleton Avatar - 아바타 로딩용
 */
interface SkeletonAvatarProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const SkeletonAvatar: React.FC<SkeletonAvatarProps> = ({
  size = 'md',
  className,
}) => {
  const sizeStyles = {
    xs: 'w-6 h-6',
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  };

  return (
    <Skeleton
      variant="circular"
      className={cn(sizeStyles[size], className)}
    />
  );
};

/**
 * Skeleton Card - 카드 로딩용
 */
interface SkeletonCardProps {
  hasImage?: boolean;
  imageHeight?: string | number;
  lines?: number;
  className?: string;
}

export const SkeletonCard: React.FC<SkeletonCardProps> = ({
  hasImage = true,
  imageHeight = 200,
  lines = 3,
  className,
}) => {
  return (
    <div
      className={cn(
        'rounded-xl',
        'border border-[var(--border-primary)]',
        'bg-[var(--bg-secondary)]',
        'overflow-hidden',
        className
      )}
    >
      {hasImage && (
        <Skeleton
          variant="default"
          height={imageHeight}
          className="w-full rounded-none"
        />
      )}
      <div className="p-4 space-y-3">
        <Skeleton variant="text" width="70%" height={20} />
        <SkeletonText lines={lines} />
      </div>
    </div>
  );
};

/**
 * Skeleton Message - 메시지 로딩용 (AI 응답 대기)
 */
interface SkeletonMessageProps {
  type?: 'user' | 'assistant';
  className?: string;
}

export const SkeletonMessage: React.FC<SkeletonMessageProps> = ({
  type = 'assistant',
  className,
}) => {
  return (
    <div
      className={cn(
        'flex gap-3',
        type === 'user' ? 'flex-row-reverse' : 'flex-row',
        className
      )}
    >
      <SkeletonAvatar size="md" />
      <div
        className={cn(
          'flex-1 max-w-[70%] p-4 rounded-2xl',
          type === 'user'
            ? 'bg-primary-500/10 rounded-br-md'
            : 'bg-[var(--glass-bg)] backdrop-blur-xl border border-[var(--glass-border)] rounded-bl-md'
        )}
      >
        <SkeletonText lines={3} lastLineWidth="80%" />
      </div>
    </div>
  );
};

/**
 * Skeleton List - 목록 로딩용
 */
interface SkeletonListProps {
  items?: number;
  className?: string;
  itemClassName?: string;
}

export const SkeletonList: React.FC<SkeletonListProps> = ({
  items = 5,
  className,
  itemClassName,
}) => {
  return (
    <div className={cn('space-y-3', className)}>
      {Array.from({ length: items }).map((_, index) => (
        <div
          key={index}
          className={cn(
            'flex items-center gap-3 p-3',
            'rounded-lg',
            'bg-[var(--bg-secondary)]',
            itemClassName
          )}
        >
          <SkeletonAvatar size="sm" />
          <div className="flex-1 space-y-2">
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="text" width="40%" height={12} />
          </div>
        </div>
      ))}
    </div>
  );
};

/**
 * Skeleton Table - 테이블 로딩용
 */
interface SkeletonTableProps {
  rows?: number;
  columns?: number;
  className?: string;
}

export const SkeletonTable: React.FC<SkeletonTableProps> = ({
  rows = 5,
  columns = 4,
  className,
}) => {
  return (
    <div
      className={cn(
        'rounded-xl',
        'border border-[var(--border-primary)]',
        'overflow-hidden',
        className
      )}
    >
      {/* Header */}
      <div className="flex bg-[var(--bg-tertiary)] p-3 gap-4">
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton
            key={index}
            variant="text"
            className="flex-1"
            height={16}
          />
        ))}
      </div>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          className={cn(
            'flex p-3 gap-4',
            'border-t border-[var(--border-primary)]'
          )}
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton
              key={colIndex}
              variant="text"
              className="flex-1"
              height={14}
            />
          ))}
        </div>
      ))}
    </div>
  );
};

/**
 * Skeleton Inline - 인라인 스켈레톤 (버튼, 태그 등)
 */
interface SkeletonInlineProps {
  width?: string | number;
  height?: string | number;
  className?: string;
}

export const SkeletonInline: React.FC<SkeletonInlineProps> = ({
  width = 80,
  height = 32,
  className,
}) => {
  return (
    <Skeleton
      variant="rounded"
      width={width}
      height={height}
      className={className}
    />
  );
};

export default Skeleton;
