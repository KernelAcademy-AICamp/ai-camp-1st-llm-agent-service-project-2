import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { UserDocumentDetail, Summary, KeyClause, RiskAnalysis } from '../types';
import DocumentDetailLayout from '../components/DocumentDetailLayout';
import '../styles/DocumentDetail.css';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

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

  // Risk analysis state (for left panel summary)
  const [riskAnalysis, setRiskAnalysis] = useState<RiskAnalysis | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);

  const loadDocument = useCallback(async () => {
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
  }, [documentId, token]);

  const loadSummary = useCallback(async () => {
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
  }, [documentId, token]);

  const loadClauses = useCallback(async () => {
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
  }, [documentId, token]);

  const loadRiskAnalysis = useCallback(async () => {
    if (!documentId || !token) return;

    setRiskLoading(true);

    try {
      const response = await apiClient.getDocumentRiskAnalysis(documentId, token);
      if (response.risk_analysis) {
        setRiskAnalysis(response.risk_analysis);
      }
    } catch (err: any) {
      // If no risk analysis exists yet, that's okay - silently ignore
      console.log('No risk analysis found for document:', documentId);
    } finally {
      setRiskLoading(false);
    }
  }, [documentId, token]);

  useEffect(() => {
    loadDocument();
    loadSummary();
    loadClauses();
    loadRiskAnalysis();
  }, [loadDocument, loadSummary, loadClauses, loadRiskAnalysis]);

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

  const handleBack = () => {
    navigate('/documents');
  };

  // Build file URL for PDF viewer
  const getFileUrl = (): string | undefined => {
    if (!document?.original_file) return undefined;
    // If original_file is already a full URL, use it
    if (document.original_file.startsWith('http')) {
      return document.original_file;
    }
    // Otherwise, construct the full URL
    return `${API_BASE}${document.original_file}`;
  };

  if (loading) {
    return (
      <div className="document-detail-page">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>문서를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="document-detail-page">
        <div className="error-container">
          <div className="error-message">{error || '문서를 찾을 수 없습니다.'}</div>
          <button className="btn-back" onClick={handleBack}>
            목록으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="document-detail-page three-panel">
      <DocumentDetailLayout
        document={document}
        token={token || undefined}
        fileUrl={getFileUrl()}
        onDelete={handleDelete}
        deleting={deleting}
        onBack={handleBack}
        summary={summary}
        summaryLoading={summaryLoading}
        summaryError={summaryError}
        onGenerateSummary={handleGenerateSummary}
        generatingSummary={generatingSummary}
        clauses={clauses}
        clausesLoading={clausesLoading}
        clausesError={clausesError}
        onExtractClauses={handleExtractClauses}
        extractingClauses={extractingClauses}
        riskAnalysis={riskAnalysis}
        riskLoading={riskLoading}
      />
    </div>
  );
};

export default DocumentDetail;
