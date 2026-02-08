import React, { useEffect, useState, useRef } from 'react';
import { FiX, FiFileText, FiCalendar, FiHome, FiHash, FiCopy, FiCheck, FiLoader, FiLayers } from 'react-icons/fi';
import { apiClient } from '../../api/client';
import './SourceDetailModal.css';

interface SourceDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  source: {
    title?: string;
    case_number?: string;
    court?: string;
    date?: string;
    doc_type?: string;
    text_snippet?: string;
    full_text?: string;
    relevance_score?: number;
    source?: string;  // source 필드 (파일명 등)
  } | null;
}

const SourceDetailModal: React.FC<SourceDetailModalProps> = ({ isOpen, onClose, source }) => {
  const [copied, setCopied] = useState(false);
  const [isLoadingFullText, setIsLoadingFullText] = useState(false);
  const [fullDocumentText, setFullDocumentText] = useState<string | null>(null);
  const [chunkCount, setChunkCount] = useState<number>(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const highlightRef = useRef<HTMLSpanElement>(null);

  // 모달이 열릴 때 전체 문서 가져오기
  useEffect(() => {
    if (isOpen && source) {
      fetchFullDocument();
    } else {
      // 모달이 닫히면 상태 초기화
      setFullDocumentText(null);
      setChunkCount(0);
      setLoadError(null);
    }
  }, [isOpen, source]);

  const fetchFullDocument = async () => {
    if (!source) return;

    // 필터 필드와 값 결정 (우선순위: case_number > title > source)
    let filterField = '';
    let filterValue = '';

    if (source.case_number) {
      filterField = 'case_number';
      filterValue = source.case_number;
    } else if (source.title) {
      filterField = 'title';
      filterValue = source.title;
    } else if (source.source) {
      filterField = 'source';
      filterValue = source.source;
    }

    if (!filterField || !filterValue) {
      // 필터 정보가 없으면 기존 텍스트 사용
      return;
    }

    setIsLoadingFullText(true);
    setLoadError(null);

    try {
      const result = await apiClient.getFullDocument(filterField, filterValue);
      setFullDocumentText(result.full_text);
      setChunkCount(result.chunk_count);
    } catch (error) {
      console.error('Failed to fetch full document:', error);
      setLoadError('전체 문서를 불러오는데 실패했습니다.');
      // 실패 시 기존 텍스트 사용
    } finally {
      setIsLoadingFullText(false);
    }
  };

  // 하이라이트된 부분으로 스크롤
  useEffect(() => {
    if (fullDocumentText && highlightRef.current) {
      // 약간의 딜레이 후 스크롤 (렌더링 완료 대기)
      setTimeout(() => {
        highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    }
  }, [fullDocumentText]);

  if (!isOpen || !source) return null;

  // 표시할 텍스트 결정 (전체 문서 > full_text > text_snippet)
  const displayText = fullDocumentText || source.full_text || source.text_snippet || '내용이 없습니다.';

  // 미리보기 텍스트 (하이라이트 대상) - trim 처리
  const snippetText = (source.text_snippet || source.full_text || '').trim();

  // 공백/줄바꿈을 정규화하는 함수
  const normalizeText = (text: string): string => {
    return text.replace(/\s+/g, ' ').trim();
  };

  // 정규화된 텍스트에서 원본 위치 찾기
  const findOriginalPosition = (original: string, normalizedIndex: number, searchLen: number): { start: number; end: number } | null => {
    const normalizedOriginal = normalizeText(original);

    // 정규화된 텍스트에서의 위치를 원본 위치로 변환
    let origIndex = 0;
    let normIndex = 0;
    let startPos = -1;

    while (origIndex < original.length && normIndex <= normalizedIndex + searchLen) {
      // 현재 원본 위치가 공백인지 확인
      if (/\s/.test(original[origIndex])) {
        // 연속된 공백 스킵
        while (origIndex < original.length && /\s/.test(original[origIndex])) {
          if (startPos === -1 && normIndex >= normalizedIndex) {
            startPos = origIndex;
          }
          origIndex++;
        }
        if (normIndex < normalizedIndex + searchLen) {
          normIndex++; // 정규화된 버전에서는 공백 하나로 처리
        }
      } else {
        if (startPos === -1 && normIndex >= normalizedIndex) {
          startPos = origIndex;
        }
        if (normIndex >= normalizedIndex + searchLen) {
          return { start: startPos, end: origIndex };
        }
        origIndex++;
        normIndex++;
      }
    }

    if (startPos !== -1) {
      return { start: startPos, end: origIndex };
    }
    return null;
  };

  // 텍스트에 하이라이트를 적용하는 함수
  const renderHighlightedText = () => {
    // 전체 문서가 없거나, 미리보기 텍스트가 없으면 일반 텍스트 반환
    if (!fullDocumentText || !snippetText || snippetText.length < 20) {
      return displayText;
    }

    let snippetIndex = -1;
    let highlightLength = snippetText.length;
    let useNormalized = false;

    // 1. 정확히 일치하는 경우
    snippetIndex = fullDocumentText.indexOf(snippetText);

    // 2. trim된 버전으로 찾기
    if (snippetIndex === -1) {
      const trimmed = snippetText.trim();
      snippetIndex = fullDocumentText.indexOf(trimmed);
      if (snippetIndex !== -1) {
        highlightLength = trimmed.length;
      }
    }

    // 3. 공백 정규화 후 매칭 (줄바꿈, 다중 공백 등 처리)
    if (snippetIndex === -1) {
      const normalizedFull = normalizeText(fullDocumentText);
      const normalizedSnippet = normalizeText(snippetText);
      const normalizedIndex = normalizedFull.indexOf(normalizedSnippet);

      if (normalizedIndex !== -1) {
        useNormalized = true;
        const pos = findOriginalPosition(fullDocumentText, normalizedIndex, normalizedSnippet.length);
        if (pos) {
          snippetIndex = pos.start;
          highlightLength = pos.end - pos.start;
          console.log('[Highlight] Normalized match found:', { normalizedIndex, originalStart: pos.start, originalEnd: pos.end });
        }
      }
    }

    // 4. 앞 50자로 부분 매칭 시도 (더 긴 prefix 사용)
    if (snippetIndex === -1) {
      const partialSnippet = normalizeText(snippetText.substring(0, Math.min(50, snippetText.length)));
      const normalizedFull = normalizeText(fullDocumentText);
      const normalizedIndex = normalizedFull.indexOf(partialSnippet);

      if (normalizedIndex !== -1) {
        const pos = findOriginalPosition(fullDocumentText, normalizedIndex, snippetText.length);
        if (pos) {
          snippetIndex = pos.start;
          highlightLength = Math.min(pos.end - pos.start, snippetText.length + 100); // 원래 snippet 길이 + 여유분
          console.log('[Highlight] Partial match found');
        }
      }
    }

    // 5. 그래도 없으면 하이라이트 없이 반환
    if (snippetIndex === -1) {
      console.log('[Highlight] No match found. Snippet preview:', snippetText.substring(0, 50));
      return displayText;
    }

    // 하이라이트할 텍스트 길이 결정
    highlightLength = Math.min(highlightLength, fullDocumentText.length - snippetIndex);

    const beforeText = fullDocumentText.substring(0, snippetIndex);
    const highlightedText = fullDocumentText.substring(snippetIndex, snippetIndex + highlightLength);
    const afterText = fullDocumentText.substring(snippetIndex + highlightLength);

    console.log('[Highlight] Match found at index:', snippetIndex, 'length:', highlightLength);

    return (
      <>
        {beforeText}
        <span ref={highlightRef} className="source-modal-highlight">
          {highlightedText}
        </span>
        {afterText}
      </>
    );
  };

  const handleCopyText = async () => {
    try {
      await navigator.clipboard.writeText(displayText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const getDocTypeIcon = (docType: string) => {
    if (docType?.includes('판결문')) return '⚖️';
    if (docType?.includes('결정례')) return '📋';
    if (docType?.includes('법령')) return '📜';
    if (docType?.includes('해석례')) return '💡';
    return '📄';
  };

  const getDocTypeColor = (docType: string) => {
    if (docType?.includes('판결문')) return 'doc-type-precedent';
    if (docType?.includes('결정례')) return 'doc-type-decision';
    if (docType?.includes('법령')) return 'doc-type-law';
    if (docType?.includes('해석례')) return 'doc-type-interpretation';
    return 'doc-type-other';
  };

  return (
    <div className="source-modal-overlay" onClick={handleOverlayClick}>
      <div className="source-modal-container">
        <div className="source-modal-header">
          <div className="source-modal-title-wrapper">
            <span className="source-modal-icon">{getDocTypeIcon(source.doc_type || '')}</span>
            <h2 className="source-modal-title">{source.title || '문서 상세'}</h2>
          </div>
          <button className="source-modal-close" onClick={onClose}>
            <FiX size={24} />
          </button>
        </div>

        <div className="source-modal-meta">
          {source.doc_type && (
            <span className={`source-modal-tag ${getDocTypeColor(source.doc_type)}`}>
              <FiFileText size={14} />
              {source.doc_type}
            </span>
          )}
          {source.case_number && (
            <span className="source-modal-tag">
              <FiHash size={14} />
              {source.case_number}
            </span>
          )}
          {source.court && (
            <span className="source-modal-tag">
              <FiHome size={14} />
              {source.court}
            </span>
          )}
          {source.date && (
            <span className="source-modal-tag">
              <FiCalendar size={14} />
              {source.date}
            </span>
          )}
          {chunkCount > 0 && (
            <span className="source-modal-tag">
              <FiLayers size={14} />
              {chunkCount}개 청크 합침
            </span>
          )}
        </div>

        <div className="source-modal-content">
          <div className="source-modal-content-header">
            <h3>
              {isLoadingFullText ? '전체 문서 로딩 중...' :
               fullDocumentText ? '전체 문서 내용' : '문서 내용'}
            </h3>
            <button
              className={`source-modal-copy-btn ${copied ? 'copied' : ''}`}
              onClick={handleCopyText}
              title="내용 복사"
              disabled={isLoadingFullText}
            >
              {copied ? <FiCheck size={16} /> : <FiCopy size={16} />}
              {copied ? '복사됨' : '복사'}
            </button>
          </div>

          {isLoadingFullText ? (
            <div className="source-modal-loading">
              <FiLoader className="spin" size={24} />
              <span>전체 문서를 불러오는 중...</span>
            </div>
          ) : (
            <>
              {loadError && (
                <div className="source-modal-error">
                  {loadError}
                </div>
              )}
              <div className="source-modal-text">
                {renderHighlightedText()}
              </div>
            </>
          )}
        </div>

        <div className="source-modal-footer">
          <span className="source-modal-score">
            관련도: {((source.relevance_score || 0) * 100).toFixed(2)}%
          </span>
          <button className="source-modal-close-btn" onClick={onClose}>
            닫기
          </button>
        </div>
      </div>
    </div>
  );
};

export default SourceDetailModal;
