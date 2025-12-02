/**
 * UI Component - Card
 *
 * Glassmorphism 카드 컴포넌트
 * variants: default, glass, elevated, outline
 */

import React from 'react';
import { cn } from '../../lib/utils';

export interface CardProps {
  children: React.ReactNode;
  variant?: 'default' | 'glass' | 'elevated' | 'outline';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hoverable?: boolean;
  clickable?: boolean;
  className?: string;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  padding = 'md',
  hoverable = false,
  clickable = false,
  className,
  onClick,
}) => {
  // Base styles
  const baseStyles = cn(
    'rounded-xl',
    'transition-all duration-200'
  );

  // Variant styles
  const variantStyles = {
    default: cn(
      'bg-[var(--bg-secondary)]',
      'border border-[var(--border-primary)]'
    ),
    glass: cn(
      'bg-[var(--glass-bg)]',
      'backdrop-blur-xl',
      'border border-[var(--glass-border)]',
      'shadow-lg shadow-[var(--glass-shadow)]'
    ),
    elevated: cn(
      'bg-[var(--bg-secondary)]',
      'shadow-xl shadow-black/5',
      'dark:shadow-black/20'
    ),
    outline: cn(
      'bg-transparent',
      'border-2 border-[var(--border-primary)]'
    ),
  };

  // Padding styles
  const paddingStyles = {
    none: 'p-0',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };

  // Hover styles
  const hoverStyles = hoverable
    ? cn(
        'hover:shadow-xl',
        'hover:-translate-y-1',
        variant === 'glass' && 'hover:bg-[var(--glass-bg-heavy)]',
        variant !== 'glass' && 'hover:border-[var(--border-secondary)]'
      )
    : '';

  // Clickable styles
  const clickableStyles = clickable || onClick
    ? 'cursor-pointer active:scale-[0.98]'
    : '';

  return (
    <div
      className={cn(
        baseStyles,
        variantStyles[variant],
        paddingStyles[padding],
        hoverStyles,
        clickableStyles,
        className
      )}
      onClick={onClick}
      role={clickable || onClick ? 'button' : undefined}
      tabIndex={clickable || onClick ? 0 : undefined}
    >
      {children}
    </div>
  );
};

/**
 * Card Header
 */
interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  children,
  className,
  action,
}) => {
  return (
    <div
      className={cn(
        'flex items-center justify-between',
        'pb-4',
        'border-b border-[var(--border-primary)]',
        className
      )}
    >
      <div>{children}</div>
      {action && <div>{action}</div>}
    </div>
  );
};

/**
 * Card Title
 */
interface CardTitleProps {
  children: React.ReactNode;
  className?: string;
  subtitle?: string;
}

export const CardTitle: React.FC<CardTitleProps> = ({
  children,
  className,
  subtitle,
}) => {
  return (
    <div className={className}>
      <h3 className="text-lg font-semibold text-[var(--text-primary)]">
        {children}
      </h3>
      {subtitle && (
        <p className="text-sm text-[var(--text-tertiary)] mt-0.5">
          {subtitle}
        </p>
      )}
    </div>
  );
};

/**
 * Card Content
 */
interface CardContentProps {
  children: React.ReactNode;
  className?: string;
}

export const CardContent: React.FC<CardContentProps> = ({
  children,
  className,
}) => {
  return <div className={cn('py-4', className)}>{children}</div>;
};

/**
 * Card Footer
 */
interface CardFooterProps {
  children: React.ReactNode;
  className?: string;
  align?: 'left' | 'center' | 'right' | 'between';
}

export const CardFooter: React.FC<CardFooterProps> = ({
  children,
  className,
  align = 'right',
}) => {
  const alignStyles = {
    left: 'justify-start',
    center: 'justify-center',
    right: 'justify-end',
    between: 'justify-between',
  };

  return (
    <div
      className={cn(
        'flex items-center gap-3',
        'pt-4',
        'border-t border-[var(--border-primary)]',
        alignStyles[align],
        className
      )}
    >
      {children}
    </div>
  );
};

/**
 * Glass Card - Glassmorphism 특화 카드
 */
interface GlassCardProps {
  children: React.ReactNode;
  intensity?: 'light' | 'medium' | 'heavy';
  className?: string;
  hoverable?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  intensity = 'medium',
  className,
  hoverable = false,
}) => {
  const intensityStyles = {
    light: cn(
      'bg-white/5 dark:bg-white/5',
      'backdrop-blur-sm',
      'border border-white/10'
    ),
    medium: cn(
      'bg-[var(--glass-bg)]',
      'backdrop-blur-xl',
      'border border-[var(--glass-border)]'
    ),
    heavy: cn(
      'bg-[var(--glass-bg-heavy)]',
      'backdrop-blur-2xl',
      'border border-[var(--glass-border)]'
    ),
  };

  return (
    <div
      className={cn(
        'rounded-xl',
        'shadow-lg shadow-[var(--glass-shadow)]',
        'transition-all duration-200',
        intensityStyles[intensity],
        hoverable && 'hover:shadow-xl hover:-translate-y-1',
        className
      )}
    >
      {children}
    </div>
  );
};

/**
 * Info Card - 정보 표시용 카드
 */
interface InfoCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  className?: string;
}

export const InfoCard: React.FC<InfoCardProps> = ({
  title,
  value,
  icon,
  trend,
  className,
}) => {
  return (
    <Card variant="glass" className={cn('p-4', className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-[var(--text-tertiary)] mb-1">{title}</p>
          <p className="text-2xl font-bold text-[var(--text-primary)]">{value}</p>
          {trend && (
            <div
              className={cn(
                'flex items-center gap-1 mt-1 text-xs font-medium',
                trend.isPositive
                  ? 'text-[var(--color-success-500)]'
                  : 'text-[var(--color-error-500)]'
              )}
            >
              {trend.isPositive ? (
                <ArrowUpIcon className="w-3 h-3" />
              ) : (
                <ArrowDownIcon className="w-3 h-3" />
              )}
              <span>{Math.abs(trend.value)}%</span>
            </div>
          )}
        </div>
        {icon && (
          <div
            className={cn(
              'w-10 h-10 rounded-lg',
              'bg-primary-500/10',
              'flex items-center justify-center',
              'text-primary-500'
            )}
          >
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
};

// Icons
const ArrowUpIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
  </svg>
);

const ArrowDownIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
  </svg>
);

export default Card;
