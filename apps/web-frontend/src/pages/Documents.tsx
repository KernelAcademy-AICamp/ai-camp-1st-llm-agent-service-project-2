import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import {
  UserDocument,
  UserDocumentType,
  UserDocumentStatus
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

  // Drag and drop state
  const [dragging, setDragging] = useState(false);

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
      if (!uploadTitle) {
        setUploadTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  // Handle upload
  const handleUpload = async () => {
    if (!uploadFile || !uploadTitle || !token) return;

    setUploading(true);
    setError(null);

    try {
      await apiClient.uploadDocument(
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

      // Reload documents
      await loadDocuments();

      alert('문서가 성공적으로 업로드되었습니다!');
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // Status badge
  const getStatusBadge = (status: UserDocumentStatus) => {
    const badges: Record<UserDocumentStatus, { label: string; className: string }> = {
      UPLOADED: { label: '업로드됨', className: 'badge-uploaded' },
      OCR_DONE: { label: 'OCR 완료', className: 'badge-processing' },
      PREPROCESSED: { label: '전처리됨', className: 'badge-processing' },
      EMBEDDED: { label: '인덱싱 완료', className: 'badge-completed' },
      FAILED: { label: '실패', className: 'badge-failed' },
    };

    const badge = badges[status];
    return <span className={`status-badge ${badge.className}`}>{badge.label}</span>;
  };

  // Format file size
  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="documents-page">
      <div className="documents-container">
        <h1>내 문서</h1>

        {/* Upload Section */}
        <div className="upload-section">
          <h2>문서 업로드</h2>

          <div
            className={`drop-zone ${dragging ? 'dragging' : ''} ${uploadFile ? 'has-file' : ''}`}
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {uploadFile ? (
              <div className="file-selected">
                <p>📄 {uploadFile.name}</p>
                <p className="file-size">{formatFileSize(uploadFile.size)}</p>
              </div>
            ) : (
              <div className="drop-zone-content">
                <p>파일을 드래그하거나 클릭하여 업로드</p>
                <p className="supported-formats">지원 형식: PDF, DOCX, TXT (최대 10MB)</p>
              </div>
            )}
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={handleFileChange}
              style={{ display: 'none' }}
              id="file-input"
            />
            <label htmlFor="file-input" className="file-input-label">
              파일 선택
            </label>
          </div>

          {uploadFile && (
            <div className="upload-form">
              <div className="form-group">
                <label>문서 제목</label>
                <input
                  type="text"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  placeholder="문서 제목을 입력하세요"
                />
              </div>

              <div className="form-group">
                <label>문서 유형</label>
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

              <button
                className="btn-primary"
                onClick={handleUpload}
                disabled={uploading || !uploadTitle}
              >
                {uploading ? '업로드 중...' : '업로드'}
              </button>
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && <div className="error-message">{error}</div>}

        {/* Documents List */}
        <div className="documents-list">
          <h2>문서 목록</h2>

          {loading ? (
            <div className="loading">문서를 불러오는 중...</div>
          ) : documents.length === 0 ? (
            <div className="empty-state">
              <p>아직 업로드된 문서가 없습니다.</p>
            </div>
          ) : (
            <div className="document-cards">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="document-card"
                  onClick={() => navigate(`/documents/${doc.id}`)}
                >
                  <div className="document-header">
                    <h3>{doc.title}</h3>
                    {getStatusBadge(doc.status)}
                  </div>

                  <div className="document-meta">
                    <span>📁 {doc.doc_type}</span>
                    <span>📄 {formatFileSize(doc.file_size)}</span>
                    {doc.chunk_count > 0 && <span>📊 {doc.chunk_count} chunks</span>}
                  </div>

                  <div className="document-footer">
                    <span className="document-date">
                      {new Date(doc.created_at).toLocaleDateString('ko-KR')}
                    </span>
                  </div>

                  {doc.error_message && (
                    <div className="error-message">{doc.error_message}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Documents;
