import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { UserDocumentDetail, Summary, KeyClause, RiskAnalysis, AnalysisStatus, ANALYSIS_STATUS_LABELS } from '../types';
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

  // Preview clauses state (for selective addition)
  const [previewClauses, setPreviewClauses] = useState<KeyClause[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [savingSelected, setSavingSelected] = useState(false);

  // Risk analysis state (for left panel summary)
  const [riskAnalysis, setRiskAnalysis] = useState<RiskAnalysis | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);

  // Analysis status polling state
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>('none');
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, []);

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

  // Start polling for analysis status
  const startPollingAnalysisStatus = useCallback(() => {
    if (!documentId || !token) return;

    // Don't start if already polling
    if (pollingIntervalRef.current) return;

    const pollInterval = setInterval(async () => {
      try {
        const status = await apiClient.getAnalysisStatus(documentId, token);
        setAnalysisStatus(status.analysis_status);

        // Reload data when each step completes
        if (status.has_summary && !summary) {
          loadSummary();
        }
        if (status.has_clauses && clauses.length === 0) {
          loadClauses();
        }
        if (status.has_risk_analysis && !riskAnalysis) {
          loadRiskAnalysis();
        }

        // Stop polling if analysis is complete or failed
        if (status.analysis_status === 'completed' || status.analysis_status === 'failed') {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          // Final reload to get all data
          loadDocument();
        }
      } catch (err) {
        console.error('Failed to poll analysis status:', err);
      }
    }, 3000); // Poll every 3 seconds

    pollingIntervalRef.current = pollInterval;
  }, [documentId, token, summary, clauses.length, riskAnalysis, loadSummary, loadClauses, loadRiskAnalysis, loadDocument]);

  useEffect(() => {
    loadDocument();
    loadSummary();
    loadClauses();
    loadRiskAnalysis();
  }, [loadDocument, loadSummary, loadClauses, loadRiskAnalysis]);

  // Start polling if document is being analyzed
  useEffect(() => {
    if (document?.analysis_status) {
      setAnalysisStatus(document.analysis_status);

      // Start polling if analysis is in progress
      const inProgress = ['pending', 'summarizing', 'extracting_clauses', 'analyzing_risk'].includes(document.analysis_status);
      if (inProgress) {
        startPollingAnalysisStatus();
      }
    }
  }, [document?.analysis_status, startPollingAnalysisStatus]);

  const handleGenerateSummary = async () => {
    if (!documentId || !token) return;

    setGeneratingSummary(true);
    setSummaryError(null);

    try {
      // 요약만 생성 (선택적 분석)
      const response = await apiClient.analyzeDocument(documentId, token, 'summary');
      setSummary(response.summary);
    } catch (err: any) {
      setSummaryError(err.message || 'Failed to generate summary');
    } finally {
      setGeneratingSummary(false);
    }
  };

  const handleExtractClauses = async () => {
    if (!documentId || !token) return;

    setExtractingClauses(true);
    setClausesError(null);

    try {
      // 조항만 추출 (선택적 분석)
      const response = await apiClient.analyzeDocument(documentId, token, 'clauses');
      setClauses(response.clauses);
    } catch (err: any) {
      setClausesError(err.message || 'Failed to extract clauses');
    } finally {
      setExtractingClauses(false);
    }
  };

  const handleExtractPreview = async () => {
    if (!documentId || !token) return;

    setPreviewLoading(true);
    setClausesError(null);

    try {
      // 미리보기용 조항 추출 (DB 저장 없음)
      const response = await apiClient.extractClausesPreview(documentId, token);
      setPreviewClauses(response.clauses);
    } catch (err: any) {
      setClausesError(err.message || 'Failed to extract clauses');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSaveSelected = async (selectedClauses: KeyClause[]) => {
    if (!documentId || !token) return;

    setSavingSelected(true);

    try {
      // 선택된 조항만 저장
      const response = await apiClient.saveSelectedClauses(documentId, selectedClauses, token);

      // 기존 조항에 새 조항 추가
      setClauses(prev => [...prev, ...response.clauses]);

      // 미리보기 초기화
      setPreviewClauses([]);
    } catch (err: any) {
      setClausesError(err.message || 'Failed to save clauses');
    } finally {
      setSavingSelected(false);
    }
  };

  const handleCancelPreview = () => {
    setPreviewClauses([]);
  };

  const handleDelete = async () => {
    if (!documentId || !token) return;

    if (!window.confirm('정말로 이 문서를 삭제하시겠습니까?')) {
      return;
    }

    setDeleting(true);

    try {
      await apiClient.deleteUserDocument(documentId, token);
      // 삭제 성공 - 목록 페이지로 이동
      navigate('/documents', { replace: true });
    } catch (err: any) {
      // 에러 시 알림 표시
      console.error('삭제 실패:', err.message);
      alert('문서 삭제에 실패했습니다: ' + (err.message || '알 수 없는 오류'));
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
    <div className="document-detail-page">
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
        previewClauses={previewClauses}
        previewLoading={previewLoading}
        onExtractPreview={handleExtractPreview}
        onSaveSelected={handleSaveSelected}
        savingSelected={savingSelected}
        onCancelPreview={handleCancelPreview}
        riskAnalysis={riskAnalysis}
        riskLoading={riskLoading}
        analysisStatus={analysisStatus}
      />
    </div>
  );
};

export default DocumentDetail;
