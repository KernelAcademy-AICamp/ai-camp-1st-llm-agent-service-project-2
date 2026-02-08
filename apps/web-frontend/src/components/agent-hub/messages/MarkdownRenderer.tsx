/**
 * Agent Hub - Markdown Renderer Component
 *
 * AI 응답의 마크다운 콘텐츠를 렌더링
 * 코드 하이라이팅, 표, 링크, 리스트 등 지원
 */

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn, copyToClipboard } from '../../../lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className,
}) => {
  return (
    <div className={cn('markdown-content', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Headings
          h1: ({ children }) => (
            <h1 className="text-xl font-bold text-[var(--text-primary)] mt-6 mb-3 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-semibold text-[var(--text-primary)] mt-5 mb-2 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-semibold text-[var(--text-primary)] mt-4 mb-2 first:mt-0">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-sm font-semibold text-[var(--text-primary)] mt-3 mb-1 first:mt-0">
              {children}
            </h4>
          ),

          // Paragraphs
          p: ({ children }) => (
            <p className="text-[var(--text-primary)] leading-relaxed mb-3 last:mb-0">
              {children}
            </p>
          ),

          // Links
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                'text-primary-500 hover:text-primary-600',
                'underline underline-offset-2',
                'transition-colors duration-150'
              )}
            >
              {children}
            </a>
          ),

          // Lists
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-1 mb-3 text-[var(--text-primary)]">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-1 mb-3 text-[var(--text-primary)]">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-[var(--text-primary)] leading-relaxed">{children}</li>
          ),

          // Blockquote
          blockquote: ({ children }) => (
            <blockquote
              className={cn(
                'border-l-4 border-primary-500/50',
                'pl-4 py-2 my-3',
                'bg-[var(--bg-tertiary)]',
                'rounded-r-lg',
                'text-[var(--text-secondary)] italic'
              )}
            >
              {children}
            </blockquote>
          ),

          // Code blocks
          code: ({ className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '');
            const isInline = !match;

            if (isInline) {
              return (
                <code
                  className={cn(
                    'px-1.5 py-0.5',
                    'text-sm font-mono',
                    'bg-[var(--bg-tertiary)]',
                    'text-[var(--color-error-500)]',
                    'rounded'
                  )}
                  {...props}
                >
                  {children}
                </code>
              );
            }

            return (
              <CodeBlock language={match[1]} {...props}>
                {String(children).replace(/\n$/, '')}
              </CodeBlock>
            );
          },

          // Pre (code block wrapper)
          pre: ({ children }) => <>{children}</>,

          // Table
          table: ({ children }) => (
            <div className="overflow-x-auto my-4 rounded-lg border border-[var(--border-primary)]">
              <table className="w-full text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-[var(--bg-tertiary)]">{children}</thead>
          ),
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => (
            <tr className="border-b border-[var(--border-primary)] last:border-0">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-4 py-2 text-left font-semibold text-[var(--text-primary)]">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-2 text-[var(--text-secondary)]">{children}</td>
          ),

          // Horizontal rule
          hr: () => <hr className="my-6 border-[var(--border-primary)]" />,

          // Strong and emphasis
          strong: ({ children }) => (
            <strong className="font-semibold text-[var(--text-primary)]">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-[var(--text-primary)]">{children}</em>
          ),

          // Strikethrough
          del: ({ children }) => (
            <del className="line-through text-[var(--text-tertiary)]">{children}</del>
          ),

          // Image
          img: ({ src, alt }) => (
            <img
              src={src}
              alt={alt}
              className={cn(
                'max-w-full h-auto',
                'rounded-lg',
                'my-4',
                'border border-[var(--border-primary)]'
              )}
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

/**
 * Code Block Component with copy functionality
 */
interface CodeBlockProps {
  language: string;
  children: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ language, children }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const success = await copyToClipboard(children);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="relative group my-4">
      {/* Language badge & copy button */}
      <div
        className={cn(
          'flex items-center justify-between',
          'px-4 py-2',
          'bg-[var(--bg-tertiary)]',
          'border border-b-0 border-[var(--border-primary)]',
          'rounded-t-lg'
        )}
      >
        <span className="text-xs font-medium text-[var(--text-tertiary)] uppercase">
          {language}
        </span>
        <button
          onClick={handleCopy}
          className={cn(
            'flex items-center gap-1',
            'px-2 py-1',
            'text-xs text-[var(--text-tertiary)]',
            'rounded',
            'hover:bg-[var(--border-primary)]',
            'hover:text-[var(--text-secondary)]',
            'transition-colors duration-150'
          )}
        >
          {copied ? (
            <>
              <CheckIcon className="w-3.5 h-3.5" />
              <span>복사됨</span>
            </>
          ) : (
            <>
              <CopyIcon className="w-3.5 h-3.5" />
              <span>복사</span>
            </>
          )}
        </button>
      </div>

      {/* Code content */}
      <pre
        className={cn(
          'overflow-x-auto',
          'p-4',
          'bg-[#1e1e1e]',
          'text-[#d4d4d4]',
          'text-sm font-mono',
          'leading-relaxed',
          'border border-t-0 border-[var(--border-primary)]',
          'rounded-b-lg'
        )}
      >
        <code>{children}</code>
      </pre>
    </div>
  );
};

// Icons
const CopyIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
    />
  </svg>
);

const CheckIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

export default MarkdownRenderer;
