/**
 * UI Component - Tag/Badge
 *
 * 상태나 카테고리를 표시하는 태그 컴포넌트
 * variants: default, primary, success, warning, error, info
 * sizes: sm, md, lg
 */

import React from 'react';
import { cn } from '../../lib/utils';

export interface TagProps {
  children: React.ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info';
  size?: 'sm' | 'md' | 'lg';
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  onRemove?: () => void;
  clickable?: boolean;
  className?: string;
  onClick?: () => void;
}

export const Tag: React.FC<TagProps> = ({
  children,
  variant = 'default',
  size = 'md',
  leftIcon,
  rightIcon,
  onRemove,
  clickable = false,
  className,
  onClick,
}) => {
  // Base styles
  const baseStyles = cn(
    'inline-flex items-center',
    'font-medium',
    'rounded-full',
    'transition-all duration-200',
    'select-none'
  );

  // Variant styles
  const variantStyles = {
    default: cn(
      'bg-[var(--bg-tertiary)]',
      'text-[var(--text-primary)]',
      'border border-[var(--border-primary)]'
    ),
    primary: cn(
      'bg-primary-500/10',
      'text-primary-600',
      'border border-primary-500/20'
    ),
    success: cn(
      'bg-[var(--color-success-50)]',
      'text-[var(--color-success-700)]',
      'border border-[var(--color-success-200)]'
    ),
    warning: cn(
      'bg-[var(--color-warning-50)]',
      'text-[var(--color-warning-700)]',
      'border border-[var(--color-warning-200)]'
    ),
    error: cn(
      'bg-[var(--color-error-50)]',
      'text-[var(--color-error-700)]',
      'border border-[var(--color-error-200)]'
    ),
    info: cn(
      'bg-[var(--color-info-50)]',
      'text-[var(--color-info-700)]',
      'border border-[var(--color-info-200)]'
    ),
  };

  // Size styles
  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-2.5 py-1 text-xs gap-1.5',
    lg: 'px-3 py-1.5 text-sm gap-2',
  };

  // Hover styles for clickable
  const hoverStyles = clickable || onClick
    ? 'cursor-pointer hover:scale-105 hover:shadow-sm'
    : '';

  // Icon size based on tag size
  const iconSizeStyles = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  };

  const Element = clickable || onClick ? 'button' : 'span';

  return (
    <Element
      className={cn(
        baseStyles,
        variantStyles[variant],
        sizeStyles[size],
        hoverStyles,
        className
      )}
      onClick={onClick}
      type={Element === 'button' ? 'button' : undefined}
    >
      {leftIcon && (
        <span className={cn('flex-shrink-0', iconSizeStyles[size])}>
          {leftIcon}
        </span>
      )}

      <span className="truncate">{children}</span>

      {rightIcon && (
        <span className={cn('flex-shrink-0', iconSizeStyles[size])}>
          {rightIcon}
        </span>
      )}

      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className={cn(
            'flex-shrink-0 ml-0.5',
            'rounded-full',
            'hover:bg-black/10 dark:hover:bg-white/10',
            'transition-colors duration-150',
            iconSizeStyles[size]
          )}
          aria-label="Remove tag"
        >
          <CloseIcon className="w-full h-full" />
        </button>
      )}
    </Element>
  );
};

/**
 * Badge - 숫자나 짧은 텍스트를 표시하는 배지
 */
export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  dot = false,
  className,
}) => {
  // Variant styles
  const variantStyles = {
    default: 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]',
    primary: 'bg-primary-500 text-white',
    success: 'bg-[var(--color-success-500)] text-white',
    warning: 'bg-[var(--color-warning-500)] text-white',
    error: 'bg-[var(--color-error-500)] text-white',
  };

  // Size styles
  const sizeStyles = {
    sm: dot ? 'w-2 h-2' : 'min-w-4 h-4 px-1 text-[10px]',
    md: dot ? 'w-2.5 h-2.5' : 'min-w-5 h-5 px-1.5 text-xs',
    lg: dot ? 'w-3 h-3' : 'min-w-6 h-6 px-2 text-sm',
  };

  if (dot) {
    return (
      <span
        className={cn(
          'inline-block rounded-full',
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
      />
    );
  }

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center',
        'font-semibold',
        'rounded-full',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
    >
      {children}
    </span>
  );
};

/**
 * Status Tag - 상태를 표시하는 특화된 태그
 */
export type StatusType = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';

interface StatusTagProps {
  status: StatusType;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const statusConfig: Record<StatusType, { label: string; variant: TagProps['variant'] }> = {
  pending: { label: '대기 중', variant: 'default' },
  in_progress: { label: '진행 중', variant: 'primary' },
  completed: { label: '완료', variant: 'success' },
  failed: { label: '실패', variant: 'error' },
  cancelled: { label: '취소됨', variant: 'warning' },
};

export const StatusTag: React.FC<StatusTagProps> = ({
  status,
  size = 'md',
  className,
}) => {
  const config = statusConfig[status];

  return (
    <Tag
      variant={config.variant}
      size={size}
      className={className}
      leftIcon={<StatusDot status={status} />}
    >
      {config.label}
    </Tag>
  );
};

// Status dot indicator
const StatusDot: React.FC<{ status: StatusType }> = ({ status }) => {
  const colorStyles: Record<StatusType, string> = {
    pending: 'bg-[var(--text-tertiary)]',
    in_progress: 'bg-primary-500 animate-pulse',
    completed: 'bg-[var(--color-success-500)]',
    failed: 'bg-[var(--color-error-500)]',
    cancelled: 'bg-[var(--color-warning-500)]',
  };

  return <span className={cn('w-1.5 h-1.5 rounded-full', colorStyles[status])} />;
};

// Close icon
const CloseIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

export default Tag;
