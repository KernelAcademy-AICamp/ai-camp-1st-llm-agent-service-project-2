import React, { useState, useCallback, useMemo } from 'react';
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
  viewMode?: 'original' | 'text';
}

const DocumentViewer: React.FC<DocumentViewerProps> = ({ document, fileUrl, viewMode = 'text' }) => {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [pdfError, setPdfError] = useState<string | null>(null);

  const isPdf = document.file_type?.toLowerCase().includes('pdf') || false;
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

  // 청크들을 페이지별로 그룹화하고 연속된 텍스트로 결합
  const groupedContent = useMemo(() => {
    if (!hasChunks) return [];

    const chunks = document.chunks;
    const pageGroups: { pageNumber: number | null; text: string }[] = [];
    let currentPage: number | null = null;
    let currentText = '';

    chunks.forEach((chunk: DocumentChunk, index: number) => {
      const chunkPage = chunk.page_number || null;

      if (chunkPage !== currentPage && currentText) {
        pageGroups.push({ pageNumber: currentPage, text: currentText.trim() });
        currentText = '';
      }

      currentPage = chunkPage;
      currentText += chunk.text + '\n\n';

      // 마지막 청크 처리
      if (index === chunks.length - 1 && currentText) {
        pageGroups.push({ pageNumber: currentPage, text: currentText.trim() });
      }
    });

    return pageGroups;
  }, [document.chunks, hasChunks]);

  const renderPdfViewer = () => {
    if (!fileUrl) {
      return (
        <div className="viewer-message">
          <p>PDF 파일 URL이 없습니다.</p>
          <p className="viewer-hint">문서 내용을 확인해주세요.</p>
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

  const renderTextViewer = () => {
    if (!hasChunks) {
      return (
        <div className="viewer-message">
          <p>문서 내용이 없습니다.</p>
          <p className="viewer-hint">문서 처리가 완료되면 내용이 표시됩니다.</p>
        </div>
      );
    }

    // 페이지 구분이 있는 경우와 없는 경우 처리
    const hasPageNumbers = groupedContent.some(g => g.pageNumber !== null);

    return (
      <div className="text-viewer">
        <div className="text-content">
          {hasPageNumbers ? (
            // 페이지 구분이 있는 경우
            groupedContent.map((group, index) => (
              <div key={index} className="text-page-section">
                {group.pageNumber && (
                  <div className="page-divider">
                    <span>페이지 {group.pageNumber}</span>
                  </div>
                )}
                <div className="text-body">{group.text}</div>
              </div>
            ))
          ) : (
            // 페이지 구분 없이 연속 텍스트
            <div className="text-body">
              {groupedContent.map(g => g.text).join('\n\n')}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="document-viewer">
      {viewMode === 'original' && isPdf && fileUrl ? renderPdfViewer() : renderTextViewer()}
    </div>
  );
};

export default DocumentViewer;
