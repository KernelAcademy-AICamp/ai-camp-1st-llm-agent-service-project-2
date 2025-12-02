/**
 * UI Component - Avatar
 *
 * 이미지 또는 이니셜을 표시하는 아바타 컴포넌트
 * sizes: xs, sm, md, lg, xl
 * variants: default, gradient
 */

import React, { useState } from 'react';
import { cn } from '../../lib/utils';

export interface AvatarProps {
  src?: string;
  alt?: string;
  name?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'default' | 'gradient' | 'outline';
  status?: 'online' | 'offline' | 'busy' | 'away';
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({
  src,
  alt,
  name,
  size = 'md',
  variant = 'default',
  status,
  className,
}) => {
  const [imageError, setImageError] = useState(false);
  const showFallback = !src || imageError;

  // Get initials from name
  const getInitials = (name?: string): string => {
    if (!name) return '?';
    const words = name.trim().split(/\s+/);
    if (words.length === 1) {
      return words[0].charAt(0).toUpperCase();
    }
    return (words[0].charAt(0) + words[words.length - 1].charAt(0)).toUpperCase();
  };

  // Size styles
  const sizeStyles = {
    xs: 'w-6 h-6 text-xs',
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base',
    xl: 'w-16 h-16 text-lg',
  };

  // Variant styles
  const variantStyles = {
    default: 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]',
    gradient: 'bg-gradient-to-br from-primary-400 to-primary-600 text-white',
    outline: 'bg-transparent border-2 border-[var(--border-primary)] text-[var(--text-secondary)]',
  };

  // Status indicator size
  const statusSizeStyles = {
    xs: 'w-1.5 h-1.5 border',
    sm: 'w-2 h-2 border',
    md: 'w-2.5 h-2.5 border-2',
    lg: 'w-3 h-3 border-2',
    xl: 'w-4 h-4 border-2',
  };

  // Status colors
  const statusColorStyles = {
    online: 'bg-[var(--color-success-500)]',
    offline: 'bg-[var(--text-tertiary)]',
    busy: 'bg-[var(--color-error-500)]',
    away: 'bg-[var(--color-warning-500)]',
  };

  return (
    <div className={cn('relative inline-flex', className)}>
      <div
        className={cn(
          'rounded-full',
          'flex items-center justify-center',
          'font-semibold',
          'overflow-hidden',
          'shadow-md',
          sizeStyles[size],
          showFallback && variantStyles[variant]
        )}
      >
        {showFallback ? (
          <span>{getInitials(name)}</span>
        ) : (
          <img
            src={src}
            alt={alt || name || 'Avatar'}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        )}
      </div>

      {/* Status Indicator */}
      {status && (
        <span
          className={cn(
            'absolute bottom-0 right-0',
            'rounded-full',
            'border-[var(--bg-primary)]',
            statusSizeStyles[size],
            statusColorStyles[status]
          )}
        />
      )}
    </div>
  );
};

/**
 * Avatar Group - 여러 아바타를 겹쳐서 표시
 */
interface AvatarGroupProps {
  children: React.ReactNode;
  max?: number;
  size?: AvatarProps['size'];
  className?: string;
}

export const AvatarGroup: React.FC<AvatarGroupProps> = ({
  children,
  max = 4,
  size = 'md',
  className,
}) => {
  const childArray = React.Children.toArray(children);
  const visibleAvatars = childArray.slice(0, max);
  const remaining = childArray.length - max;

  // Overlap styles based on size
  const overlapStyles = {
    xs: '-ml-1.5',
    sm: '-ml-2',
    md: '-ml-2.5',
    lg: '-ml-3',
    xl: '-ml-4',
  };

  return (
    <div className={cn('flex items-center', className)}>
      {visibleAvatars.map((child, index) => (
        <div
          key={index}
          className={cn(
            'relative',
            'ring-2 ring-[var(--bg-primary)]',
            'rounded-full',
            index > 0 && overlapStyles[size]
          )}
          style={{ zIndex: visibleAvatars.length - index }}
        >
          {React.isValidElement(child)
            ? React.cloneElement(child as React.ReactElement<AvatarProps>, { size })
            : child}
        </div>
      ))}

      {remaining > 0 && (
        <div
          className={cn(
            'relative',
            'ring-2 ring-[var(--bg-primary)]',
            'rounded-full',
            overlapStyles[size]
          )}
          style={{ zIndex: 0 }}
        >
          <Avatar
            name={`+${remaining}`}
            size={size}
            variant="default"
          />
        </div>
      )}
    </div>
  );
};

/**
 * User Avatar - 사용자 정보와 함께 표시
 */
interface UserAvatarProps extends AvatarProps {
  title?: string;
  subtitle?: string;
  titleClassName?: string;
  subtitleClassName?: string;
}

export const UserAvatar: React.FC<UserAvatarProps> = ({
  title,
  subtitle,
  titleClassName,
  subtitleClassName,
  ...avatarProps
}) => {
  return (
    <div className="flex items-center gap-3">
      <Avatar {...avatarProps} />
      {(title || subtitle) && (
        <div className="flex flex-col min-w-0">
          {title && (
            <span
              className={cn(
                'text-sm font-medium text-[var(--text-primary)] truncate',
                titleClassName
              )}
            >
              {title}
            </span>
          )}
          {subtitle && (
            <span
              className={cn(
                'text-xs text-[var(--text-tertiary)] truncate',
                subtitleClassName
              )}
            >
              {subtitle}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default Avatar;
