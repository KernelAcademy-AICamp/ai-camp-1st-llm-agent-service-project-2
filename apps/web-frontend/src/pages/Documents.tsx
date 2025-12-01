import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import {
  UserDocument,
  UserDocumentType,
  UserDocumentStatus,
  AnalysisStatus,
  ANALYSIS_STATUS_LABELS
} from '../types';
import '../styles/Documents.css';

const Documents: React.FC = () => {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [documents, setDocuments] = useState<UserDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDocType, setUploadDocType] = useState<UserDocumentType>('CONTRACT');
  const [showUploadForm, setShowUploadForm] = useState(false);

  // Drag and drop state
  const [dragging, setDragging] = useState(false);

  // Guide banner state
  const [showGuideBanner, setShowGuideBanner] = useState(() => {
    return localStorage.getItem('hideDocumentsGuide') !== 'true';
  });

  // Polling state for analysis status
  const pollingIntervalsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const dismissGuideBanner = () => {
    setShowGuideBanner(false);
    localStorage.setItem('hideDocumentsGuide', 'true');
  };

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      pollingIntervalsRef.current.forEach((interval) => clearInterval(interval));
      pollingIntervalsRef.current.clear();
    };
  }, []);

  // Load documents
  const loadDocuments = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getUserDocuments(token);
      setDocuments(response.results);
    } catch (err: any) {
      setError(err.message || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Handle file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadFile(file);
      setShowUploadForm(true);
      if (!uploadTitle) {
        setUploadTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  // Handle drag and drop
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      setUploadFile(file);
      setShowUploadForm(true);
      if (!uploadTitle) {
        setUploadTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  // Start polling for document analysis status
  const startPollingAnalysisStatus = useCallback((documentId: string) => {
    if (!token) return;

    // Don't start polling if already polling for this document
    if (pollingIntervalsRef.current.has(documentId)) return;

    const pollInterval = setInterval(async () => {
      try {
        const status = await apiClient.getAnalysisStatus(documentId, token);

        // Update document in list with new status
        setDocuments(prev => prev.map(doc =>
          doc.id === documentId
            ? {
                ...doc,
                analysis_status: status.analysis_status,
                analysis_status_display: status.analysis_status_display,
                analysis_error: status.analysis_error
              }
            : doc
        ));

        // Stop polling if analysis is complete or failed
        if (status.analysis_status === 'completed' || status.analysis_status === 'failed') {
          clearInterval(pollInterval);
          pollingIntervalsRef.current.delete(documentId);
        }
      } catch (err) {
        console.error('Failed to poll analysis status:', err);
      }
    }, 3000); // Poll every 3 seconds

    pollingIntervalsRef.current.set(documentId, pollInterval);
  }, [token]);

  // Handle upload and start analysis (replaces old handleUpload)
  const handleUploadAndAnalyze = async () => {
    if (!uploadFile || !uploadTitle || !token) return;

    setUploading(true);
    setError(null);

    try {
      // Upload and start auto-analysis
      const response = await apiClient.uploadAndAnalyze(
        uploadFile,
        uploadTitle,
        uploadDocType,
        'ko',
        token
      );

      // Reset form
      setUploadFile(null);
      setUploadTitle('');
      setUploadDocType('CONTRACT');
      setShowUploadForm(false);

      // Reload documents to get the new one
      await loadDocuments();

      // Start polling for this document's analysis status
      startPollingAnalysisStatus(response.document.id);
    } catch (err: any) {
      setError(err.message || 'Upload and analyze failed');
    } finally {
      setUploading(false);
    }
  };

  // Start polling for documents that are currently being analyzed
  useEffect(() => {
    documents.forEach(doc => {
      const status = doc.analysis_status;
      if (status && status !== 'none' && status !== 'completed' && status !== 'failed') {
        startPollingAnalysisStatus(doc.id);
      }
    });
  }, [documents, startPollingAnalysisStatus]);

  const cancelUpload = () => {
    setUploadFile(null);
    setUploadTitle('');
    setUploadDocType('CONTRACT');
    setShowUploadForm(false);
  };

  // Status badge
  const getStatusBadge = (status: UserDocumentStatus) => {
    const badges: Record<UserDocumentStatus, { label: string; className: string }> = {
      UPLOADED: { label: '업로드됨', className: 'badge-uploaded' },
      OCR_DONE: { label: 'OCR 완료', className: 'badge-processing' },
      PREPROCESSED: { label: '전처리중', className: 'badge-processing' },
      EMBEDDED: { label: '완료', className: 'badge-completed' },
      FAILED: { label: '실패', className: 'badge-failed' },
    };

    const badge = badges[status];
    return <span className={`status-badge ${badge.className}`}>{badge.label}</span>;
  };

  // Analysis status badge
  const getAnalysisStatusBadge = (analysisStatus: AnalysisStatus | undefined) => {
    if (!analysisStatus || analysisStatus === 'none') {
      return <span className="analysis-badge analysis-none">-</span>;
    }

    const badgeConfig: Record<AnalysisStatus, { className: string; icon?: string }> = {
      none: { className: 'analysis-none' },
      pending: { className: 'analysis-pending', icon: '...' },
      summarizing: { className: 'analysis-progress', icon: '1/3' },
      extracting_clauses: { className: 'analysis-progress', icon: '2/3' },
      analyzing_risk: { className: 'analysis-progress', icon: '3/3' },
      completed: { className: 'analysis-completed' },
      failed: { className: 'analysis-failed' },
    };

    const config = badgeConfig[analysisStatus];
    const label = ANALYSIS_STATUS_LABELS[analysisStatus];

    // Show spinner for in-progress states
    const isInProgress = ['pending', 'summarizing', 'extracting_clauses', 'analyzing_risk'].includes(analysisStatus);

    return (
      <span className={`analysis-badge ${config.className}`}>
        {isInProgress && (
          <span className="analysis-spinner"></span>
        )}
        {config.icon && <span className="analysis-step">{config.icon}</span>}
        {label}
      </span>
    );
  };

  // Format file size
  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const docTypeLabels: Record<string, string> = {
    CONTRACT: '계약서',
    CASE: '사건',
    STATUTE: '법령',
    PRECEDENT: '판례',
    OTHER: '기타'
  };

  return (
    <div className="documents-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1>내 문서</h1>
          <p className="page-subtitle">업로드한 문서를 AI가 분석하여 법률 리서치에 활용합니다</p>
        </div>
        <label htmlFor="file-input" className="btn-upload-new">
          + 새 문서 업로드
        </label>
        <input
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFileChange}
          style={{ display: 'none' }}
          id="file-input"
        />
      </div>

      {/* Upload Form Modal */}
      {showUploadForm && uploadFile && (
        <div className="upload-form-card">
          <div className="upload-form-header">
            <h3>문서 업로드</h3>
            <button className="btn-close" onClick={cancelUpload}>×</button>
          </div>
          <div className="upload-form-body">
            <div className="selected-file">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14,2 14,8 20,8" />
              </svg>
              <span className="file-name">{uploadFile.name}</span>
              <span className="file-size">{formatFileSize(uploadFile.size)}</span>
            </div>
            <div className="form-fields">
              <div className="form-group">
                <label>제목</label>
                <input
                  type="text"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  placeholder="문서 제목"
                />
              </div>
              <div className="form-group">
                <label>유형</label>
                <select
                  value={uploadDocType}
                  onChange={(e) => setUploadDocType(e.target.value as UserDocumentType)}
                >
                  <option value="CONTRACT">계약서</option>
                  <option value="CASE">사건 문서</option>
                  <option value="STATUTE">법령</option>
                  <option value="PRECEDENT">판례</option>
                  <option value="OTHER">기타</option>
                </select>
              </div>
            </div>
          </div>
          <div className="upload-form-footer">
            <button className="btn-cancel" onClick={cancelUpload}>취소</button>
            <button
              className="btn-submit btn-analyze"
              onClick={handleUploadAndAnalyze}
              disabled={uploading || !uploadTitle}
            >
              {uploading ? '업로드 및 분석 중...' : '분석하기'}
            </button>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      {/* Guide Banner - shown when documents exist */}
      {showGuideBanner && documents.length > 0 && !loading && (
        <div className="guide-banner">
          <div className="guide-banner-content">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4" />
              <path d="M12 8h.01" />
            </svg>
            <span>
              업로드된 문서는 <strong>법률 리서치</strong>에서 관련 판례 검색 시 참고 자료로 활용됩니다.
              문서를 클릭하면 AI 분석 결과를 확인할 수 있습니다.
            </span>
          </div>
          <button className="guide-banner-close" onClick={dismissGuideBanner}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      )}

      {/* Drop Zone (shown when dragging or no documents) */}
      <div
        className={`drop-zone ${dragging ? 'dragging' : ''}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={{ display: dragging || documents.length === 0 ? 'flex' : 'none' }}
      >
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17,8 12,3 7,8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <p>파일을 여기에 드래그하거나 상단 버튼을 클릭하세요</p>
        <span>PDF, DOCX, TXT (최대 10MB)</span>
      </div>

      {/* Documents Table */}
      {!loading && documents.length > 0 && (
        <div className="documents-table-container">
          <table className="documents-table">
            <thead>
              <tr>
                <th>문서명</th>
                <th>유형</th>
                <th>크기</th>
                <th>업로드일</th>
                <th>상태</th>
                <th>분석 상태</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} onClick={() => navigate(`/documents/${doc.id}`)}>
                  <td className="doc-title-cell">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14,2 14,8 20,8" />
                    </svg>
                    {doc.title}
                  </td>
                  <td>{docTypeLabels[doc.doc_type] || doc.doc_type}</td>
                  <td>{formatFileSize(doc.file_size)}</td>
                  <td>{new Date(doc.created_at).toLocaleDateString('ko-KR')}</td>
                  <td>{getStatusBadge(doc.status)}</td>
                  <td>{getAnalysisStatusBadge(doc.analysis_status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>문서를 불러오는 중...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && documents.length === 0 && !dragging && (
        <div className="empty-state-container">
          <div className="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
            <h3>문서를 업로드해 보세요</h3>
            <p>계약서, 사건 기록 등 법률 문서를 업로드하면 AI가 분석합니다</p>
          </div>

          <div className="empty-state-features">
            <div className="feature-item">
              <div className="feature-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <path d="M21 21l-4.35-4.35" />
                </svg>
              </div>
              <div className="feature-text">
                <strong>관련 판례 검색</strong>
                <span>문서 내용을 기반으로 유사 판례를 찾아줍니다</span>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
                  <path d="M12 20V10" />
                  <path d="M18 20V4" />
                  <path d="M6 20v-4" />
                </svg>
              </div>
              <div className="feature-text">
                <strong>리스크 분석</strong>
                <span>계약서의 불리한 조항이나 누락 사항을 점검합니다</span>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <div className="feature-text">
                <strong>AI 질의응답</strong>
                <span>문서 내용에 대해 AI에게 직접 질문할 수 있습니다</span>
              </div>
            </div>
          </div>

          <div className="empty-state-formats">
            지원 형식: PDF, DOCX, TXT (최대 10MB)
          </div>
        </div>
      )}
    </div>
  );
};

export default Documents;
