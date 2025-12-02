/**
 * UI Component - Button
 *
 * 재사용 가능한 버튼 컴포넌트
 * variants: primary, secondary, ghost, danger
 * sizes: sm, md, lg
 * icon 버튼 지원
 */

import React, { forwardRef } from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  iconOnly?: boolean;
  fullWidth?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      iconOnly = false,
      fullWidth = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading;

    // Base styles
    const baseStyles = cn(
      'inline-flex items-center justify-center',
      'font-medium',
      'border-none',
      'cursor-pointer',
      'transition-all duration-200',
      'select-none',
      'focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:cursor-not-allowed disabled:opacity-50'
    );

    // Variant styles
    const variantStyles = {
      primary: cn(
        'bg-gradient-to-br from-primary-500 to-primary-600',
        'text-white',
        'shadow-md shadow-primary-500/20',
        'hover:shadow-lg hover:shadow-primary-500/30',
        'hover:-translate-y-0.5',
        'active:translate-y-0',
        'focus:ring-primary-500/50'
      ),
      secondary: cn(
        'bg-[var(--bg-secondary)]',
        'text-[var(--text-primary)]',
        'border border-[var(--border-primary)]',
        'hover:bg-[var(--bg-tertiary)]',
        'hover:border-[var(--border-secondary)]',
        'focus:ring-[var(--border-focus)]'
      ),
      ghost: cn(
        'bg-transparent',
        'text-[var(--text-secondary)]',
        'hover:bg-[var(--bg-tertiary)]',
        'hover:text-[var(--text-primary)]',
        'focus:ring-[var(--border-focus)]'
      ),
      danger: cn(
        'bg-gradient-to-br from-[var(--color-error-500)] to-[var(--color-error-600)]',
        'text-white',
        'shadow-md shadow-[var(--color-error-500)]/20',
        'hover:shadow-lg hover:shadow-[var(--color-error-500)]/30',
        'hover:-translate-y-0.5',
        'active:translate-y-0',
        'focus:ring-[var(--color-error-500)]/50'
      ),
    };

    // Size styles
    const sizeStyles = {
      sm: cn(
        iconOnly ? 'w-8 h-8' : 'px-3 py-1.5',
        'text-xs',
        'rounded-lg',
        'gap-1.5'
      ),
      md: cn(
        iconOnly ? 'w-10 h-10' : 'px-4 py-2',
        'text-sm',
        'rounded-xl',
        'gap-2'
      ),
      lg: cn(
        iconOnly ? 'w-12 h-12' : 'px-6 py-3',
        'text-base',
        'rounded-xl',
        'gap-2.5'
      ),
    };

    // Icon only styles
    const iconOnlyStyles = iconOnly ? 'rounded-full p-0' : '';

    return (
      <button
        ref={ref}
        className={cn(
          baseStyles,
          variantStyles[variant],
          sizeStyles[size],
          iconOnlyStyles,
          fullWidth && 'w-full',
          className
        )}
        disabled={isDisabled}
        {...props}
      >
        {isLoading ? (
          <LoadingSpinner size={size} />
        ) : (
          <>
            {leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
            {!iconOnly && children}
            {rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

/**
 * Loading Spinner
 */
interface LoadingSpinnerProps {
  size: 'sm' | 'md' | 'lg';
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size }) => {
  const sizeClasses = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  return (
    <svg
      className={cn(sizeClasses[size], 'animate-spin')}
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
};

/**
 * Icon Button - 편의 컴포넌트
 */
export interface IconButtonProps extends Omit<ButtonProps, 'iconOnly' | 'children'> {
  icon: React.ReactNode;
  'aria-label': string;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, className, ...props }, ref) => {
    return (
      <Button ref={ref} iconOnly className={className} {...props}>
        {icon}
      </Button>
    );
  }
);

IconButton.displayName = 'IconButton';

/**
 * Button Group
 */
interface ButtonGroupProps {
  children: React.ReactNode;
  className?: string;
  orientation?: 'horizontal' | 'vertical';
}

export const ButtonGroup: React.FC<ButtonGroupProps> = ({
  children,
  className,
  orientation = 'horizontal',
}) => {
  return (
    <div
      className={cn(
        'inline-flex',
        orientation === 'horizontal' ? 'flex-row' : 'flex-col',
        '[&>button]:rounded-none',
        orientation === 'horizontal'
          ? '[&>button:first-child]:rounded-l-xl [&>button:last-child]:rounded-r-xl'
          : '[&>button:first-child]:rounded-t-xl [&>button:last-child]:rounded-b-xl',
        '[&>button:not(:first-child)]:-ml-px',
        className
      )}
      role="group"
    >
      {children}
    </div>
  );
};

export default Button;
