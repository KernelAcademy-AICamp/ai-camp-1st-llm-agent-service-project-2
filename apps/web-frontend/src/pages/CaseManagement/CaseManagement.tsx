import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiFolder, FiUpload, FiPlus, FiFileText, FiTrash2, FiEye, FiAlertCircle, FiEdit, FiCpu, FiLoader } from 'react-icons/fi';
import apiClient from '../../api/client';
import { CaseAnalysis, CaseListItem } from '../../types';
import './CaseManagement.css';

const CaseManagement: React.FC = () => {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseAnalysis | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  // 사건 목록 로드
  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    try {
      const data = await apiClient.getCases();
      setCases(data.cases || []);
    } catch (error) {
      console.error('Error loading cases:', error);
    }
  };

  // 파일 선택 핸들러
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(files);
    setUploadError(null);
  };

  // 파일 업로드 및 분석
  const handleUploadFiles = async () => {
    if (selectedFiles.length === 0) {
      setUploadError('파일을 선택해주세요.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      const analysis: CaseAnalysis = await apiClient.uploadCaseFiles(selectedFiles);

      // 사건 목록 새로고침
      await loadCases();

      // 업로드된 사건 선택
      setSelectedCase(analysis);

      // 모달 닫기
      setShowUploadModal(false);
      setSelectedFiles([]);
    } catch (error: any) {
      setUploadError(error.message || '파일 업로드 중 오류가 발생했습니다.');
    } finally {
      setIsUploading(false);
    }
  };

  // 사건 상세 정보 로드
  const handleViewCase = async (caseId: string) => {
    try {
      const analysis: CaseAnalysis = await apiClient.getCase(caseId);
      setSelectedCase(analysis);
    } catch (error) {
      console.error('Error loading case details:', error);
    }
  };

  // 사건 삭제
  const handleDeleteCase = async (caseId: string) => {
    if (!window.confirm('정말로 이 사건을 삭제하시겠습니까?')) return;

    try {
      await apiClient.deleteCase(caseId);

      // 사건 목록 새로고침
      await loadCases();

      // 선택된 사건이 삭제된 경우 초기화
      if (selectedCase?.case_id === caseId) {
        setSelectedCase(null);
      }
    } catch (error) {
      console.error('Error deleting case:', error);
      alert('사건 삭제 중 오류가 발생했습니다.');
    }
  };

  return (
    <div className="case-management">
      <div className="page-header">
        <div>
          <h2>사건 관리</h2>
          <p>사건별로 문서를 정리하고 AI 분석을 활용하세요</p>
        </div>
        <button className="btn-primary" onClick={() => setShowUploadModal(true)}>
          <FiPlus /> 새 사건 업로드
        </button>
      </div>

      <div className="case-content">
        {/* 사건 목록 */}
        <div className="case-list">
          <h3>사건 목록 ({cases.length})</h3>
          {cases.length === 0 ? (
            <div className="empty-state">
              <FiFolder />
              <p>아직 등록된 사건이 없습니다.</p>
              <button className="btn-secondary" onClick={() => setShowUploadModal(true)}>
                <FiUpload /> 첫 사건 업로드하기
              </button>
            </div>
          ) : (
            <div className="case-items">
              {cases.map((caseItem) => (
                <div
                  key={caseItem.case_id}
                  className={`case-item ${selectedCase?.case_id === caseItem.case_id ? 'active' : ''}`}
                >
                  <div className="case-item-content" onClick={() => handleViewCase(caseItem.case_id)}>
                    <div className="case-item-header">
                      <FiFolder />
                      <h4>{caseItem.case_name}</h4>
                    </div>
                    <p className="case-item-summary">{caseItem.summary}</p>
                    <div className="case-item-meta">
                      <span>{caseItem.document_count}개 문서</span>
                      <span>{new Date(caseItem.created_at * 1000).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="case-item-actions">
                    <button
                      className="btn-icon"
                      onClick={() => handleViewCase(caseItem.case_id)}
                      title="상세 보기"
                    >
                      <FiEye />
                    </button>
                    <button
                      className="btn-icon btn-danger"
                      onClick={() => handleDeleteCase(caseItem.case_id)}
                      title="삭제"
                    >
                      <FiTrash2 />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 사건 상세 정보 */}
        <div className="case-detail">
          {selectedCase ? (
            <>
              <div className="detail-header">
                <h3>{selectedCase.suggested_case_name}</h3>
                <button
                  className="btn-icon btn-danger"
                  onClick={() => handleDeleteCase(selectedCase.case_id)}
                >
                  <FiTrash2 /> 삭제
                </button>
              </div>

              <div className="detail-section">
                <h4>사건 요약</h4>
                <p>{selectedCase.summary}</p>
              </div>

              {/* 시나리오 정보 및 문서 생성 */}
              {selectedCase.scenario && (
                <div className="detail-section scenario-section">
                  <h4>AI 분석 - 사건 유형</h4>
                  <div className="scenario-info-card">
                    <div className="scenario-name">
                      <FiCpu />
                      <span>{selectedCase.scenario.scenario_name}</span>
                      <span className="confidence">
                        {Math.round(selectedCase.scenario.confidence * 100)}% 확신
                      </span>
                    </div>
                    <p className="scenario-desc">
                      {selectedCase.scenario.description}
                    </p>
                    <button
                      className="btn-primary"
                      onClick={() => navigate(`/docs?caseId=${selectedCase.case_id}`)}
                    >
                      <FiEdit /> 문서 생성하기
                    </button>
                  </div>
                </div>
              )}

              <div className="detail-section">
                <h4>업로드된 문서 ({selectedCase.uploaded_files.length})</h4>
                <ul className="file-list">
                  {selectedCase.uploaded_files.map((file, idx) => (
                    <li key={idx}>
                      <FiFileText />
                      <span>{file.filename}</span>
                      <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
                    </li>
                  ))}
                </ul>
              </div>

              {selectedCase.document_types.length > 0 && (
                <div className="detail-section">
                  <h4>문서 유형</h4>
                  <div className="tag-list">
                    {selectedCase.document_types.map((type, idx) => (
                      <span key={idx} className="tag">{type}</span>
                    ))}
                  </div>
                </div>
              )}

              {selectedCase.parties && Object.keys(selectedCase.parties).length > 0 && (
                <div className="detail-section">
                  <h4>당사자</h4>
                  <ul>
                    {Object.entries(selectedCase.parties).map(([role, name]) => (
                      <li key={role}>
                        <strong>{role}:</strong> {name}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedCase.issues.length > 0 && (
                <div className="detail-section">
                  <h4>주요 쟁점</h4>
                  <ul>
                    {selectedCase.issues.map((issue, idx) => (
                      <li key={idx}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedCase.key_dates && Object.keys(selectedCase.key_dates).length > 0 && (
                <div className="detail-section">
                  <h4>주요 날짜</h4>
                  <ul>
                    {Object.entries(selectedCase.key_dates).map(([label, date]) => (
                      <li key={label}>
                        <strong>{label}:</strong> {date}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedCase.related_cases.length > 0 && (
                <div className="detail-section">
                  <h4>관련 판례</h4>
                  <ul className="related-cases">
                    {selectedCase.related_cases.map((relatedCase, idx) => (
                      <li key={idx}>
                        <strong>{relatedCase.title}</strong>
                        <p>{relatedCase.summary}</p>
                        <span className="relevance">관련도: {relatedCase.relevance}%</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedCase.suggested_next_steps.length > 0 && (
                <div className="detail-section">
                  <h4>다음 단계 제안</h4>
                  <ul>
                    {selectedCase.suggested_next_steps.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <FiFolder />
              <p>사건을 선택하면 상세 정보를 확인할 수 있습니다.</p>
            </div>
          )}
        </div>
      </div>

      {/* 파일 업로드 모달 */}
      {showUploadModal && (
        <div className="modal-overlay" onClick={() => !isUploading && setShowUploadModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>새 사건 업로드</h3>
            <p>PDF, DOCX, TXT 파일을 업로드하여 AI 분석을 받으세요.</p>

            <div className="file-upload-area">
              <input
                type="file"
                id="file-input"
                multiple
                accept=".pdf,.docx,.doc,.txt"
                onChange={handleFileSelect}
                disabled={isUploading}
              />
              <label htmlFor="file-input" className="file-upload-label">
                <FiUpload />
                <span>파일 선택 (PDF, DOCX, TXT)</span>
              </label>

              {selectedFiles.length > 0 && (
                <div className="selected-files">
                  <h4>선택된 파일 ({selectedFiles.length})</h4>
                  <ul>
                    {selectedFiles.map((file, idx) => (
                      <li key={idx}>
                        <FiFileText />
                        <span>{file.name}</span>
                        <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {uploadError && (
              <div className="error-message">
                <FiAlertCircle />
                <span>{uploadError}</span>
              </div>
            )}

            {isUploading && (
              <div className="upload-loading-overlay">
                <div className="upload-spinner">
                  <FiLoader className="spinner-icon" />
                </div>
                <p className="upload-status">파일 업로드 및 AI 분석 중...</p>
                <p className="upload-detail">문서 파싱, 쟁점 분석, 관련 판례 검색 진행 중</p>
              </div>
            )}

            <div className="modal-actions">
              <button
                className="btn-secondary"
                onClick={() => setShowUploadModal(false)}
                disabled={isUploading}
              >
                취소
              </button>
              <button
                className="btn-primary"
                onClick={handleUploadFiles}
                disabled={isUploading || selectedFiles.length === 0}
              >
                {isUploading ? '업로드 중...' : '업로드 및 분석'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CaseManagement;