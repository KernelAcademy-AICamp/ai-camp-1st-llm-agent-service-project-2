/**
 * Agent Hub - Header Component
 *
 * 로고, 테마 토글, 사용자 메뉴를 포함하는 헤더
 * Glassmorphism 효과 적용
 */

import React, { useState, useRef, useEffect } from 'react';
import { cn } from '../../../lib/utils';
import { useTheme } from '../../../hooks';
import { useAuth } from '../../../contexts/AuthContext';

interface HeaderProps {
  onMenuClick?: () => void;
  onContextClick?: () => void;
  showMenuButton?: boolean;
  className?: string;
}

export const Header: React.FC<HeaderProps> = ({
  onMenuClick,
  onContextClick,
  showMenuButton = false,
  className,
}) => {
  const { theme, toggleTheme } = useTheme();
  const { user, isAuthenticated, logout } = useAuth();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div
      className={cn(
        'h-full px-4 lg:px-6',
        'flex items-center justify-between',
        className
      )}
    >
      {/* Left Section */}
      <div className="flex items-center gap-3">
        {/* Mobile Menu Button */}
        {showMenuButton && (
          <button
            onClick={onMenuClick}
            className={cn(
              'p-2 rounded-lg',
              'text-[var(--text-secondary)]',
              'hover:bg-[var(--bg-tertiary)]',
              'transition-colors duration-200'
            )}
            aria-label="메뉴 열기"
          >
            <MenuIcon className="w-5 h-5" />
          </button>
        )}

        {/* Logo */}
        <a
          href="/agent-hub"
          className="flex items-center gap-2 text-[var(--text-primary)] hover:opacity-80 transition-opacity"
        >
          <div
            className={cn(
              'w-8 h-8 rounded-lg',
              'bg-gradient-to-br from-primary-500 to-primary-600',
              'flex items-center justify-center',
              'text-white font-bold text-sm'
            )}
          >
            AH
          </div>
          <span className="font-semibold text-lg hidden sm:block">Agent Hub</span>
        </a>
      </div>

      {/* Center Section - Search (Desktop only) */}
      <div className="hidden lg:flex flex-1 max-w-md mx-8">
        <div
          className={cn(
            'w-full relative',
            'flex items-center',
            'px-4 py-2',
            'rounded-xl',
            'bg-[var(--bg-tertiary)]',
            'border border-[var(--border-primary)]',
            'focus-within:border-[var(--border-focus)]',
            'focus-within:ring-2 focus-within:ring-[var(--input-focus-ring)]',
            'transition-all duration-200'
          )}
        >
          <SearchIcon className="w-4 h-4 text-[var(--text-tertiary)] mr-2 flex-shrink-0" />
          <input
            type="text"
            placeholder="대화 검색..."
            className={cn(
              'flex-1 bg-transparent',
              'text-sm text-[var(--text-primary)]',
              'placeholder:text-[var(--text-tertiary)]',
              'outline-none'
            )}
          />
          <kbd
            className={cn(
              'hidden sm:flex items-center gap-1',
              'px-2 py-0.5',
              'text-xs text-[var(--text-tertiary)]',
              'bg-[var(--bg-secondary)]',
              'rounded border border-[var(--border-primary)]'
            )}
          >
            <span>⌘</span>
            <span>K</span>
          </kbd>
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-2">
        {/* Mobile Context Panel Button */}
        {showMenuButton && (
          <button
            onClick={onContextClick}
            className={cn(
              'p-2 rounded-lg',
              'text-[var(--text-secondary)]',
              'hover:bg-[var(--bg-tertiary)]',
              'transition-colors duration-200'
            )}
            aria-label="컨텍스트 패널 열기"
          >
            <PanelRightIcon className="w-5 h-5" />
          </button>
        )}

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className={cn(
            'p-2 rounded-lg',
            'text-[var(--text-secondary)]',
            'hover:bg-[var(--bg-tertiary)]',
            'hover:text-[var(--text-primary)]',
            'transition-all duration-200'
          )}
          aria-label={`${theme === 'dark' ? '라이트' : '다크'} 모드로 전환`}
        >
          {theme === 'dark' ? (
            <SunIcon className="w-5 h-5" />
          ) : (
            <MoonIcon className="w-5 h-5" />
          )}
        </button>

        {/* User Menu */}
        <div ref={userMenuRef} className="relative">
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className={cn(
              'flex items-center gap-2',
              'p-1.5 pr-3 rounded-full',
              'bg-[var(--bg-tertiary)]',
              'hover:bg-[var(--border-primary)]',
              'transition-colors duration-200'
            )}
          >
            <div
              className={cn(
                'w-7 h-7 rounded-full',
                'bg-gradient-to-br from-secondary-400 to-secondary-600',
                'flex items-center justify-center',
                'text-white text-xs font-semibold'
              )}
            >
              {isAuthenticated && user?.full_name
                ? user.full_name.charAt(0).toUpperCase()
                : 'G'}
            </div>
            <ChevronDownIcon className="w-4 h-4 text-[var(--text-tertiary)]" />
          </button>

          {/* Dropdown Menu */}
          {userMenuOpen && (
            <div
              className={cn(
                'absolute right-0 top-full mt-2',
                'w-56 py-2',
                'rounded-xl',
                'bg-[var(--glass-bg-heavy)]',
                'backdrop-blur-xl',
                'border border-[var(--border-primary)]',
                'shadow-xl',
                'animate-scale-in origin-top-right',
                'z-[var(--z-dropdown)]'
              )}
            >
              {isAuthenticated && user ? (
                <>
                  <div className="px-4 py-2 border-b border-[var(--border-primary)]">
                    <p className="font-medium text-sm text-[var(--text-primary)]">
                      {user.full_name || '사용자'}
                    </p>
                    <p className="text-xs text-[var(--text-tertiary)] truncate">
                      {user.email}
                    </p>
                  </div>
                  <MenuItem icon={<SettingsIcon />} label="설정" href="/settings" />
                  <MenuItem icon={<HelpIcon />} label="도움말" href="/help" />
                  <div className="border-t border-[var(--border-primary)] mt-1 pt-1">
                    <MenuItem
                      icon={<LogoutIcon />}
                      label="로그아웃"
                      onClick={() => {
                        logout();
                        setUserMenuOpen(false);
                      }}
                      variant="danger"
                    />
                  </div>
                </>
              ) : (
                <>
                  <MenuItem icon={<LoginIcon />} label="로그인" href="/login" />
                  <MenuItem icon={<SignupIcon />} label="회원가입" href="/signup" />
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Menu Item Component
interface MenuItemProps {
  icon: React.ReactNode;
  label: string;
  href?: string;
  onClick?: () => void;
  variant?: 'default' | 'danger';
}

const MenuItem: React.FC<MenuItemProps> = ({
  icon,
  label,
  href,
  onClick,
  variant = 'default',
}) => {
  const className = cn(
    'flex items-center gap-3 w-full',
    'px-4 py-2',
    'text-sm',
    variant === 'danger'
      ? 'text-[var(--color-error-500)] hover:bg-[var(--color-error-50)]'
      : 'text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]',
    'transition-colors duration-150'
  );

  const content = (
    <>
      <span className="w-4 h-4 opacity-70">{icon}</span>
      {label}
    </>
  );

  if (href) {
    return (
      <a href={href} className={className}>
        {content}
      </a>
    );
  }

  return (
    <button onClick={onClick} className={className}>
      {content}
    </button>
  );
};

// Icons - 인라인 스타일로 크기 고정
const MenuIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '20px', height: '20px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
  </svg>
);

const SearchIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const SunIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '20px', height: '20px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
  </svg>
);

const MoonIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '20px', height: '20px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
  </svg>
);

const PanelRightIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '20px', height: '20px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
  </svg>
);

const ChevronDownIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const SettingsIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

const HelpIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const LogoutIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
  </svg>
);

const LoginIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
  </svg>
);

const SignupIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
  </svg>
);

export default Header;
