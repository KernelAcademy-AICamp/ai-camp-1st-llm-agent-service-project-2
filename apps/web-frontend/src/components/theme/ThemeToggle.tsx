/**
 * Theme Toggle Component
 *
 * 다크모드/라이트모드 전환 버튼
 * 태양/달 아이콘과 전환 애니메이션
 */

import React from 'react';
import { cn } from '../../lib/utils';
import { useTheme } from '../../hooks';

export interface ThemeToggleProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'icon' | 'switch' | 'button';
  className?: string;
  showLabel?: boolean;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({
  size = 'md',
  variant = 'icon',
  className,
  showLabel = false,
}) => {
  const { theme, toggleTheme, isDark } = useTheme();

  // Size configurations
  const sizeConfig = {
    sm: { button: 'w-8 h-8', icon: 'w-4 h-4' },
    md: { button: 'w-10 h-10', icon: 'w-5 h-5' },
    lg: { button: 'w-12 h-12', icon: 'w-6 h-6' },
  };

  if (variant === 'switch') {
    return <ThemeSwitch size={size} className={className} />;
  }

  if (variant === 'button') {
    return (
      <button
        onClick={toggleTheme}
        className={cn(
          'inline-flex items-center gap-2',
          'px-4 py-2 rounded-xl',
          'bg-[var(--bg-secondary)]',
          'border border-[var(--border-primary)]',
          'text-[var(--text-primary)]',
          'hover:bg-[var(--bg-tertiary)]',
          'transition-all duration-200',
          className
        )}
        aria-label={`${isDark ? '라이트' : '다크'} 모드로 전환`}
      >
        <span className={cn(sizeConfig[size].icon, 'transition-transform duration-300')}>
          {isDark ? <SunIcon /> : <MoonIcon />}
        </span>
        {showLabel && (
          <span className="text-sm font-medium">
            {isDark ? '라이트 모드' : '다크 모드'}
          </span>
        )}
      </button>
    );
  }

  // Default: icon variant
  return (
    <button
      onClick={toggleTheme}
      className={cn(
        'relative',
        'flex items-center justify-center',
        sizeConfig[size].button,
        'rounded-full',
        'bg-[var(--bg-secondary)]',
        'border border-[var(--border-primary)]',
        'text-[var(--text-secondary)]',
        'hover:bg-[var(--bg-tertiary)]',
        'hover:text-[var(--text-primary)]',
        'hover:rotate-12',
        'active:scale-95',
        'transition-all duration-200',
        'focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:ring-offset-2',
        className
      )}
      aria-label={`${isDark ? '라이트' : '다크'} 모드로 전환`}
    >
      <span
        className={cn(
          sizeConfig[size].icon,
          'transition-transform duration-300',
          'hover:scale-110'
        )}
      >
        {isDark ? <SunIcon /> : <MoonIcon />}
      </span>
    </button>
  );
};

/**
 * Theme Switch - 토글 스위치 스타일
 */
interface ThemeSwitchProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const ThemeSwitch: React.FC<ThemeSwitchProps> = ({ size = 'md', className }) => {
  const { isDark, toggleTheme } = useTheme();

  const sizeConfig = {
    sm: { track: 'w-10 h-5', thumb: 'w-4 h-4', translate: 'translate-x-5', icon: 'w-2.5 h-2.5' },
    md: { track: 'w-14 h-7', thumb: 'w-6 h-6', translate: 'translate-x-7', icon: 'w-3.5 h-3.5' },
    lg: { track: 'w-18 h-9', thumb: 'w-8 h-8', translate: 'translate-x-9', icon: 'w-4 h-4' },
  };

  return (
    <button
      role="switch"
      aria-checked={isDark}
      onClick={toggleTheme}
      className={cn(
        'relative inline-flex items-center',
        sizeConfig[size].track,
        'rounded-full',
        'transition-colors duration-300',
        isDark
          ? 'bg-gradient-to-r from-indigo-600 to-purple-600'
          : 'bg-gradient-to-r from-amber-400 to-orange-400',
        'focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:ring-offset-2',
        className
      )}
      aria-label={`${isDark ? '라이트' : '다크'} 모드로 전환`}
    >
      {/* Background icons */}
      <span className="absolute inset-0 flex items-center justify-between px-1.5">
        <MoonIcon className={cn(sizeConfig[size].icon, 'text-white/70')} />
        <SunIcon className={cn(sizeConfig[size].icon, 'text-white/70')} />
      </span>

      {/* Thumb */}
      <span
        className={cn(
          'absolute left-0.5',
          sizeConfig[size].thumb,
          'rounded-full',
          'bg-white',
          'shadow-md',
          'flex items-center justify-center',
          'transition-transform duration-300 ease-in-out',
          isDark && sizeConfig[size].translate
        )}
      >
        {isDark ? (
          <MoonIcon className={cn(sizeConfig[size].icon, 'text-indigo-600')} />
        ) : (
          <SunIcon className={cn(sizeConfig[size].icon, 'text-amber-500')} />
        )}
      </span>
    </button>
  );
};

/**
 * Theme Dropdown - 드롭다운 메뉴 스타일
 */
interface ThemeDropdownProps {
  className?: string;
}

export const ThemeDropdown: React.FC<ThemeDropdownProps> = ({ className }) => {
  const { theme, toggleTheme, isDark } = useTheme();
  const [isOpen, setIsOpen] = React.useState(false);

  const options = [
    { value: 'light', label: '라이트', icon: <SunIcon className="w-4 h-4" /> },
    { value: 'dark', label: '다크', icon: <MoonIcon className="w-4 h-4" /> },
    { value: 'system', label: '시스템', icon: <SystemIcon className="w-4 h-4" /> },
  ];

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2',
          'px-3 py-2 rounded-lg',
          'bg-[var(--bg-secondary)]',
          'border border-[var(--border-primary)]',
          'text-[var(--text-primary)]',
          'hover:bg-[var(--bg-tertiary)]',
          'transition-colors duration-200'
        )}
      >
        {isDark ? <MoonIcon className="w-4 h-4" /> : <SunIcon className="w-4 h-4" />}
        <span className="text-sm">{isDark ? '다크' : '라이트'}</span>
        <ChevronDownIcon className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <div
          className={cn(
            'absolute right-0 top-full mt-2',
            'w-36 py-1',
            'rounded-xl',
            'bg-[var(--glass-bg-heavy)]',
            'backdrop-blur-xl',
            'border border-[var(--border-primary)]',
            'shadow-xl',
            'z-50',
            'animate-scale-in origin-top-right'
          )}
        >
          {options.map((option) => (
            <button
              key={option.value}
              onClick={() => {
                if (option.value !== 'system') {
                  if ((option.value === 'dark') !== isDark) {
                    toggleTheme();
                  }
                }
                setIsOpen(false);
              }}
              className={cn(
                'flex items-center gap-2 w-full',
                'px-3 py-2',
                'text-sm text-[var(--text-primary)]',
                'hover:bg-[var(--bg-tertiary)]',
                'transition-colors duration-150',
                theme === option.value && 'bg-primary-500/10 text-primary-500'
              )}
            >
              {option.icon}
              <span>{option.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// Icons
const SunIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
    />
  </svg>
);

const MoonIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
    />
  </svg>
);

const SystemIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
    />
  </svg>
);

const ChevronDownIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

export default ThemeToggle;
