import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { UserDocumentDetail, Summary, KeyClause } from '../types';
import SummarySection from '../components/SummarySection';
import ClauseList from '../components/ClauseList';
import RiskAnalysisSection from '../components/RiskAnalysisSection';
import CaseAnalysisSection from '../components/CaseAnalysisSection';
import ModelComparisonSection from '../components/ModelComparisonSection';
import '../styles/DocumentDetail.css';

const DocumentDetail: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const { token } = useAuth();
  const navigate = useNavigate();

  const [document, setDocument] = useState<UserDocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Summary state
  const [summary, setSummary] = useState<Summary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [generatingSummary, setGeneratingSummary] = useState(false);

  // Clauses state
  const [clauses, setClauses] = useState<KeyClause[]>([]);
  const [clausesLoading, setClausesLoading] = useState(false);
  const [clausesError, setClausesError] = useState<string | null>(null);
  const [extractingClauses, setExtractingClauses] = useState(false);

  useEffect(() => {
    loadDocument();
    loadSummary();
    loadClauses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId, token]);

  const loadDocument = async () => {
    if (!documentId || !token) return;

    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.getUserDocumentDetail(documentId, token);
      setDocument(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async () => {
    if (!documentId || !token) return;

    setSummaryLoading(true);
    setSummaryError(null);

    try {
      const response = await apiClient.getDocumentSummary(documentId, token);
      setSummary(response.summary);
    } catch (err: any) {
      setSummaryError(err.message || 'Failed to load summary');
    } finally {
      setSummaryLoading(false);
    }
  };

  const loadClauses = async () => {
    if (!documentId || !token) return;

    setClausesLoading(true);
    setClausesError(null);

    try {
      const response = await apiClient.getDocumentClauses(documentId, token);
      setClauses(response.clauses);
    } catch (err: any) {
      setClausesError(err.message || 'Failed to load clauses');
    } finally {
      setClausesLoading(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (!documentId || !token) return;

    setGeneratingSummary(true);
    setSummaryError(null);

    try {
      const response = await apiClient.analyzeDocument(documentId, token);
      setSummary(response.summary);
      alert('요약이 성공적으로 생성되었습니다!');
    } catch (err: any) {
      setSummaryError(err.message || 'Failed to generate summary');
      alert(`요약 생성 실패: ${err.message}`);
    } finally {
      setGeneratingSummary(false);
    }
  };

  const handleExtractClauses = async () => {
    if (!documentId || !token) return;

    setExtractingClauses(true);
    setClausesError(null);

    try {
      const response = await apiClient.analyzeDocument(documentId, token);
      setClauses(response.clauses);
      alert('조항이 성공적으로 추출되었습니다!');
    } catch (err: any) {
      setClausesError(err.message || 'Failed to extract clauses');
      alert(`조항 추출 실패: ${err.message}`);
    } finally {
      setExtractingClauses(false);
    }
  };

  const handleDelete = async () => {
    if (!documentId || !token) return;

    if (!window.confirm('정말로 이 문서를 삭제하시겠습니까?')) {
      return;
    }

    setDeleting(true);

    try {
      await apiClient.deleteUserDocument(documentId, token);
      alert('문서가 삭제되었습니다.');
      navigate('/documents');
    } catch (err: any) {
      alert(`삭제 실패: ${err.message}`);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="document-detail-page">
        <div className="loading">문서를 불러오는 중...</div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="document-detail-page">
        <div className="error-message">{error || '문서를 찾을 수 없습니다.'}</div>
        <button onClick={() => navigate('/documents')}>목록으로 돌아가기</button>
      </div>
    );
  }

  return (
    <div className="document-detail-page">
      <div className="document-detail-container">
        <div className="document-header">
          <button className="btn-back" onClick={() => navigate('/documents')}>
            ← 돌아가기
          </button>

          <h1>{document.title}</h1>

          <div className="document-actions">
            <button
              className="btn-danger"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? '삭제 중...' : '문서 삭제'}
            </button>
          </div>
        </div>

        {/* Document Info */}
        <div className="document-info">
          <div className="info-row">
            <span className="info-label">상태:</span>
            <span className={`status-badge status-${document.status.toLowerCase()}`}>
              {document.status}
            </span>
          </div>

          <div className="info-row">
            <span className="info-label">유형:</span>
            <span>{document.doc_type}</span>
          </div>

          <div className="info-row">
            <span className="info-label">언어:</span>
            <span>{document.language === 'ko' ? '한국어' : '영어'}</span>
          </div>

          {document.file_size && (
            <div className="info-row">
              <span className="info-label">파일 크기:</span>
              <span>
                {document.file_size < 1024 * 1024
                  ? `${(document.file_size / 1024).toFixed(1)} KB`
                  : `${(document.file_size / (1024 * 1024)).toFixed(1)} MB`}
              </span>
            </div>
          )}

          {document.file_type && (
            <div className="info-row">
              <span className="info-label">파일 타입:</span>
              <span>{document.file_type}</span>
            </div>
          )}

          {document.page_count && (
            <div className="info-row">
              <span className="info-label">페이지 수:</span>
              <span>{document.page_count}</span>
            </div>
          )}

          <div className="info-row">
            <span className="info-label">청크 수:</span>
            <span>{document.chunk_count}</span>
          </div>

          <div className="info-row">
            <span className="info-label">업로드 일시:</span>
            <span>{new Date(document.created_at).toLocaleString('ko-KR')}</span>
          </div>

          {document.error_message && (
            <div className="error-message">
              <strong>오류:</strong> {document.error_message}
            </div>
          )}
        </div>

        {/* AI Analysis Section */}
        <div className="analysis-section">
          <SummarySection
            summary={summary}
            loading={summaryLoading}
            error={summaryError}
            onGenerate={handleGenerateSummary}
            generating={generatingSummary}
          />

          <ClauseList
            clauses={clauses}
            loading={clausesLoading}
            error={clausesError}
            onExtract={handleExtractClauses}
            extracting={extractingClauses}
          />

          <RiskAnalysisSection
            documentId={document.id}
            token={token || undefined}
            documentTitle={document.title}
          />

          {/* Show Case Analysis only for CASE type documents */}
          {document.doc_type === 'CASE' && (
            <CaseAnalysisSection
              documentId={document.id}
              token={token || undefined}
              documentTitle={document.title}
            />
          )}

          {/* LLM Model Comparison Section */}
          <ModelComparisonSection
            documentId={document.id}
            documentTitle={document.title}
            documentText={
              document.chunks && document.chunks.length > 0
                ? document.chunks.map(c => c.text).join('\n\n')
                : undefined
            }
            token={token || undefined}
          />
        </div>

        {/* Chunks */}
        {document.chunks && document.chunks.length > 0 && (
          <div className="chunks-section">
            <h2>문서 청크 ({document.chunks.length})</h2>

            <div className="chunks-list">
              {document.chunks.slice(0, 10).map((chunk) => (
                <div key={chunk.id} className="chunk-card">
                  <div className="chunk-header">
                    <span className="chunk-index">Chunk #{chunk.chunk_index}</span>
                    {chunk.embedding_id && (
                      <span className="chunk-badge">✓ 인덱싱됨</span>
                    )}
                  </div>

                  <div className="chunk-content">
                    <p>{chunk.text.substring(0, 200)}...</p>
                  </div>

                  <div className="chunk-meta">
                    {chunk.page_number && <span>페이지 {chunk.page_number}</span>}
                    {chunk.token_count && <span>{chunk.token_count} tokens</span>}
                  </div>
                </div>
              ))}

              {document.chunks.length > 10 && (
                <div className="chunks-notice">
                  처음 10개의 청크만 표시됩니다. (총 {document.chunks.length}개)
                </div>
              )}
            </div>
          </div>
        )}

        {/* Processing Status */}
        {document.status !== 'EMBEDDED' && document.status !== 'FAILED' && (
          <div className="processing-notice">
            <p>⏳ 문서 처리가 진행 중입니다...</p>
            <p className="small">
              업로드 → 전처리 → 임베딩 단계를 거쳐 RAG 검색에 사용할 수 있습니다.
            </p>
          </div>
        )}

        {document.is_processing_complete && (
          <div className="success-notice">
            <p>✅ 문서 처리가 완료되었습니다!</p>
            <p className="small">이 문서는 이제 RAG 검색에 사용할 수 있습니다.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentDetail;
