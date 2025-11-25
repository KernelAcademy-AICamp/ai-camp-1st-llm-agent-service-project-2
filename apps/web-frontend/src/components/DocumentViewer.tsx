import React, { useState, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { UserDocumentDetail, DocumentChunk } from '../types';
import '../styles/DocumentViewer.css';

// PDF.js worker 설정
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface DocumentViewerProps {
  document: UserDocumentDetail;
  fileUrl?: string;
}

const DocumentViewer: React.FC<DocumentViewerProps> = ({ document, fileUrl }) => {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set());

  const isPdf = document.file_type?.toLowerCase() === 'pdf';
  const hasChunks = document.chunks && document.chunks.length > 0;

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNumber(1);
    setPdfError(null);
  }, []);

  const onDocumentLoadError = useCallback((error: Error) => {
    console.error('PDF load error:', error);
    setPdfError('PDF 파일을 불러올 수 없습니다.');
  }, []);

  const goToPrevPage = () => setPageNumber((prev) => Math.max(prev - 1, 1));
  const goToNextPage = () => setPageNumber((prev) => Math.min(prev + 1, numPages || 1));

  const zoomIn = () => setScale((prev) => Math.min(prev + 0.25, 2.5));
  const zoomOut = () => setScale((prev) => Math.max(prev - 0.25, 0.5));
  const resetZoom = () => setScale(1.0);

  const toggleChunkExpand = (chunkId: string) => {
    setExpandedChunks((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(chunkId)) {
        newSet.delete(chunkId);
      } else {
        newSet.add(chunkId);
      }
      return newSet;
    });
  };

  const renderPdfViewer = () => {
    if (!fileUrl) {
      return (
        <div className="viewer-message">
          <p>PDF 파일 URL이 없습니다.</p>
          <p className="viewer-hint">문서 청크를 확인해주세요.</p>
        </div>
      );
    }

    if (pdfError) {
      return (
        <div className="viewer-error">
          <p>{pdfError}</p>
          <button className="btn-retry" onClick={() => setPdfError(null)}>
            다시 시도
          </button>
        </div>
      );
    }

    return (
      <>
        <div className="pdf-controls">
          <div className="pdf-nav">
            <button onClick={goToPrevPage} disabled={pageNumber <= 1}>
              ◀ 이전
            </button>
            <span className="page-info">
              {pageNumber} / {numPages || '-'}
            </span>
            <button onClick={goToNextPage} disabled={pageNumber >= (numPages || 1)}>
              다음 ▶
            </button>
          </div>
          <div className="pdf-zoom">
            <button onClick={zoomOut} disabled={scale <= 0.5}>
              −
            </button>
            <button onClick={resetZoom}>
              {Math.round(scale * 100)}%
            </button>
            <button onClick={zoomIn} disabled={scale >= 2.5}>
              +
            </button>
          </div>
        </div>
        <div className="pdf-container">
          <Document
            file={fileUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={<div className="pdf-loading">PDF 로딩 중...</div>}
          >
            <Page
              pageNumber={pageNumber}
              scale={scale}
              loading={<div className="page-loading">페이지 로딩 중...</div>}
            />
          </Document>
        </div>
      </>
    );
  };

  const renderChunkViewer = () => {
    if (!hasChunks) {
      return (
        <div className="viewer-message">
          <p>문서 청크가 없습니다.</p>
          <p className="viewer-hint">문서 전처리가 완료되면 청크가 표시됩니다.</p>
        </div>
      );
    }

    return (
      <div className="chunks-viewer">
        <div className="chunks-header">
          <h3>문서 내용</h3>
          <span className="chunk-count">{document.chunks.length}개 청크</span>
        </div>
        <div className="chunks-list">
          {document.chunks.map((chunk: DocumentChunk) => {
            const isExpanded = expandedChunks.has(chunk.id);
            const previewText = chunk.text.substring(0, 200);
            const hasMore = chunk.text.length > 200;

            return (
              <div
                key={chunk.id}
                className={`chunk-item ${isExpanded ? 'expanded' : ''}`}
              >
                <div className="chunk-header-row">
                  <div className="chunk-info">
                    <span className="chunk-index">#{chunk.chunk_index}</span>
                    {chunk.page_number && (
                      <span className="chunk-page">p.{chunk.page_number}</span>
                    )}
                    {chunk.token_count && (
                      <span className="chunk-tokens">{chunk.token_count} tokens</span>
                    )}
                    {chunk.embedding_id && (
                      <span className="chunk-embedded-badge">임베딩됨</span>
                    )}
                  </div>
                </div>
                <div className="chunk-text">
                  {isExpanded ? chunk.text : previewText}
                  {!isExpanded && hasMore && '...'}
                </div>
                {hasMore && (
                  <button
                    className="btn-expand"
                    onClick={() => toggleChunkExpand(chunk.id)}
                  >
                    {isExpanded ? '접기' : '더 보기'}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="document-viewer">
      {isPdf && fileUrl ? renderPdfViewer() : renderChunkViewer()}
    </div>
  );
};

export default DocumentViewer;
