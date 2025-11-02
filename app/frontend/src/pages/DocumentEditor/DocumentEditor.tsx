import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FiFileText, FiEdit3, FiCpu, FiDownload, FiTrash2, FiFolder, FiAlertCircle, FiLoader, FiStar, FiCheckCircle } from 'react-icons/fi';
import apiClient from '../../api/client';
import {
  CaseListItem,
  CaseAnalysis,
  GeneratedDocument,
  DocumentDetail,
  Scenario,
  TemplateField,
  GenerationMode
} from '../../types';
import './DocumentEditor.css';

// 확장된 CaseDetail 인터페이스 (scenario 정보 포함)
interface CaseDetail extends Partial<CaseAnalysis> {
  case_id: string;
  case_name?: string;
  created_at?: number;
}

const TEMPLATE_FIELDS: Record<string, TemplateField[]> = {
  '소장': [
    { name: 'claim_amount', label: '청구 금액', type: 'number', placeholder: '예: 50000000', required: true },
    { name: 'claim_purpose', label: '청구 취지', type: 'textarea', placeholder: '피고는 원고에게 금 ○○원을 지급하라', required: true },
    { name: 'case_summary', label: '사건 개요', type: 'textarea', placeholder: '계약 체결 경위 및 채무 불이행 사실', required: false },
  ],
  '답변서': [
    { name: 'admission', label: '인정 사항', type: 'textarea', placeholder: '원고 주장 중 인정하는 부분', required: false },
    { name: 'denial', label: '부인 사항', type: 'textarea', placeholder: '원고 주장 중 부인하는 부분과 이유', required: true },
    { name: 'defense', label: '항변 내용', type: 'textarea', placeholder: '소멸시효, 상계 등', required: false },
  ],
  '고소장': [
    { name: 'suspect_name', label: '피고소인 성명', type: 'text', placeholder: '홍길동', required: true },
    { name: 'suspect_info', label: '피고소인 정보', type: 'textarea', placeholder: '생년월일, 주소 등', required: false },
    { name: 'crime_fact', label: '범죄 사실', type: 'textarea', placeholder: '육하원칙에 따른 범죄 사실 기술', required: true },
    { name: 'evidence_summary', label: '증거 개요', type: 'textarea', placeholder: '제출 증거 목록 및 설명', required: false },
  ],
  '변론요지서': [
    { name: 'defense_argument', label: '변론 요지', type: 'textarea', placeholder: '무죄 주장 근거 또는 정상 참작 사유', required: true },
    { name: 'evidence_critique', label: '검사 증거 반박', type: 'textarea', placeholder: '검사 측 증거의 문제점', required: false },
  ],
  '내용증명': [
    { name: 'recipient_name', label: '수신인', type: 'text', placeholder: '홍길동', required: true },
    { name: 'debt_amount', label: '채무 금액', type: 'number', placeholder: '예: 10000000', required: true },
    { name: 'deadline', label: '이행 기한', type: 'date', placeholder: '', required: true },
    { name: 'legal_action', label: '불이행 시 조치', type: 'text', placeholder: '예: 민사소송 제기', required: false },
  ],
};

const DocumentEditor: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [documents, setDocuments] = useState<GeneratedDocument[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<DocumentDetail | null>(null);
  const [scenarios, setScenarios] = useState<Record<string, Scenario>>({});
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [generationMode, setGenerationMode] = useState<GenerationMode>('quick');
  const [customFields, setCustomFields] = useState<Record<string, string>>({});
  const [userInstructions, setUserInstructions] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  // 사건 목록 로드
  useEffect(() => {
    loadCases();
    loadScenarios();
  }, []);

  // URL 파라미터에서 caseId 읽기
  useEffect(() => {
    const caseIdFromUrl = searchParams.get('caseId');
    if (caseIdFromUrl) {
      setSelectedCaseId(caseIdFromUrl);
    }
  }, [searchParams]);

  // 사건 선택 시 문서 목록 및 상세 정보 로드
  useEffect(() => {
    if (selectedCaseId) {
      loadDocuments(selectedCaseId);
      loadCaseDetail(selectedCaseId);
    }
  }, [selectedCaseId]);

  const loadCases = async () => {
    try {
      const data = await apiClient.getCases();
      setCases(data.cases || []);
    } catch (error) {
      console.error('Error loading cases:', error);
    }
  };

  const loadScenarios = async () => {
    try {
      const data = await apiClient.getScenarios();
      setScenarios(data.scenarios || {});
    } catch (error) {
      console.error('Error loading scenarios:', error);
    }
  };

  const loadCaseDetail = async (caseId: string) => {
    try {
      const data = await apiClient.getCase(caseId);
      setCaseDetail(data);
    } catch (error) {
      console.error('Error loading case detail:', error);
    }
  };

  const loadDocuments = async (caseId: string) => {
    try {
      const data = await apiClient.listDocuments(caseId);
      setDocuments(data.documents || []);
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  const handleGenerateDocument = async () => {
    if (!selectedCaseId || !selectedTemplate) {
      setGenerateError('사건과 템플릿을 선택해주세요.');
      return;
    }

    // 맞춤 모드일 경우 필수 필드 검증
    if (generationMode === 'custom') {
      const templateFields = TEMPLATE_FIELDS[selectedTemplate] || [];
      const requiredFields = templateFields.filter(f => f.required);
      const missingFields = requiredFields.filter(f => !customFields[f.name]);

      if (missingFields.length > 0) {
        setGenerateError(`필수 항목을 입력해주세요: ${missingFields.map(f => f.label).join(', ')}`);
        return;
      }
    }

    setIsGenerating(true);
    setGenerateError(null);

    try {
      const document: DocumentDetail = await apiClient.generateDocument({
        case_id: selectedCaseId,
        template_name: selectedTemplate,
        generation_mode: generationMode,
        custom_fields: generationMode === 'custom' ? customFields : undefined,
        user_instructions: userInstructions || undefined,
      });

      // 문서 목록 새로고침
      await loadDocuments(selectedCaseId);

      // 생성된 문서 선택
      setSelectedDocument(document);

      // 모달 닫기 및 초기화
      handleCloseModal();
    } catch (error: any) {
      setGenerateError(error.message || '문서 생성 중 오류가 발생했습니다.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleViewDocument = async (caseId: string, documentId: string) => {
    try {
      const document: DocumentDetail = await apiClient.getDocument(caseId, documentId);
      setSelectedDocument(document);
    } catch (error) {
      console.error('Error loading document:', error);
    }
  };

  const handleDeleteDocument = async (caseId: string, documentId: string) => {
    if (!window.confirm('정말로 이 문서를 삭제하시겠습니까?')) return;

    try {
      await apiClient.deleteDocument(caseId, documentId);

      // 문서 목록 새로고침
      await loadDocuments(caseId);

      // 선택된 문서가 삭제된 경우 초기화
      if (selectedDocument?.document_id === documentId) {
        setSelectedDocument(null);
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('문서 삭제 중 오류가 발생했습니다.');
    }
  };

  const handleDownloadDocument = () => {
    if (!selectedDocument) return;

    const blob = new Blob([selectedDocument.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedDocument.title}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // 모달 열기 (사건 미선택 시 안내)
  const handleOpenModal = () => {
    if (!selectedCaseId) {
      alert('먼저 왼쪽에서 사건을 선택해주세요.');
      return;
    }
    setShowGenerateModal(true);
  };

  // 모달 닫기 및 상태 초기화
  const handleCloseModal = () => {
    setShowGenerateModal(false);
    setSelectedTemplate('');
    setGenerationMode('quick');
    setCustomFields({});
    setUserInstructions('');
    setGenerateError(null);
  };

  // 템플릿 변경 시 커스텀 필드 초기화
  const handleTemplateChange = (template: string) => {
    setSelectedTemplate(template);
    setCustomFields({});
  };

  // 커스텀 필드 입력 핸들러
  const handleCustomFieldChange = (fieldName: string, value: string) => {
    setCustomFields(prev => ({
      ...prev,
      [fieldName]: value
    }));
  };

  // 추천 템플릿 (사건의 시나리오 기반)
  const getRecommendedTemplates = (): string[] => {
    if (!caseDetail?.scenario?.scenario_name || !scenarios[caseDetail.scenario.scenario_name]) {
      return [];
    }
    return scenarios[caseDetail.scenario.scenario_name].templates || [];
  };

  // 이미 생성된 템플릿 목록
  const generatedTemplateNames = documents.map(doc => doc.template_used);

  // 빠른 생성 핸들러
  const handleQuickGenerate = async (templateName: string) => {
    if (!selectedCaseId) return;

    setSelectedTemplate(templateName);
    setIsGenerating(true);
    setGenerateError(null);

    try {
      const document: DocumentDetail = await apiClient.generateDocument({
        case_id: selectedCaseId,
        template_name: templateName,
      });

      // 문서 목록 새로고침
      await loadDocuments(selectedCaseId);

      // 생성된 문서 선택
      setSelectedDocument(document);
    } catch (error: any) {
      setGenerateError(error.message || '문서 생성 중 오류가 발생했습니다.');
      alert(`문서 생성 실패: ${error.message}`);
    } finally {
      setIsGenerating(false);
      setSelectedTemplate('');
    }
  };

  // 모든 템플릿 목록 (시나리오에서 추출)
  const allTemplates = Array.from(
    new Set(
      Object.values(scenarios).flatMap((scenario) => scenario.templates)
    )
  );

  return (
    <div className="document-editor">
      <div className="page-header">
        <div>
          <h2>문서 작성</h2>
          <p>AI 어시스트로 법률 문서를 효율적으로 작성하세요</p>
        </div>
        <button
          className="btn-primary"
          onClick={handleOpenModal}
        >
          <FiCpu /> AI 문서 생성
        </button>
      </div>

      <div className="editor-content">
        {/* 사건 선택 */}
        <div className="case-selector">
          <h3>사건 선택</h3>
          {cases.length === 0 ? (
            <div className="empty-state">
              <FiFolder />
              <p>등록된 사건이 없습니다.</p>
              <small>먼저 사건을 등록해주세요.</small>
            </div>
          ) : (
            <div className="case-list-compact">
              {cases.map((caseItem) => (
                <div
                  key={caseItem.case_id}
                  className={`case-item-compact ${
                    selectedCaseId === caseItem.case_id ? 'active' : ''
                  }`}
                  onClick={() => setSelectedCaseId(caseItem.case_id)}
                >
                  <FiFolder />
                  <div className="case-item-info">
                    <h4>{caseItem.case_name}</h4>
                    <p>{caseItem.summary.substring(0, 80)}...</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 추천 템플릿 & 문서 목록 */}
        <div className="document-list">
          {!selectedCaseId ? (
            <div className="empty-state">
              <FiFileText />
              <p>사건을 선택해주세요.</p>
            </div>
          ) : (
            <>
              {/* 추천 템플릿 섹션 */}
              {caseDetail?.scenario && getRecommendedTemplates().length > 0 && (
                <div className="recommended-section">
                  <h3><FiStar /> 이 사건에 적합한 문서</h3>
                  <p className="scenario-info">
                    {caseDetail.scenario.scenario_name} ({Math.round(caseDetail.scenario.confidence * 100)}% 확신)
                  </p>
                  <div className="recommended-templates">
                    {getRecommendedTemplates().map((template, index) => {
                      const isGenerated = generatedTemplateNames.includes(template);
                      return (
                        <div key={template} className="recommended-template-card">
                          <div className="template-priority">{index + 1}순위</div>
                          <div className="template-card-content">
                            <div className="template-card-header">
                              <h4>{template}</h4>
                              {isGenerated && (
                                <span className="template-status completed">
                                  <FiCheckCircle /> 생성됨
                                </span>
                              )}
                            </div>
                            <button
                              className={isGenerated ? "btn-secondary" : "btn-primary"}
                              onClick={() => handleQuickGenerate(template)}
                              disabled={isGenerating}
                            >
                              {isGenerating && selectedTemplate === template ? (
                                <>
                                  <FiLoader className="spinner" /> 생성 중...
                                </>
                              ) : isGenerated ? (
                                <>
                                  <FiCpu /> 다시 생성
                                </>
                              ) : (
                                <>
                                  <FiCpu /> 빠른 생성
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 생성된 문서 목록 */}
              <div className="generated-section">
                <h3>생성된 문서 ({documents.length})</h3>
                {documents.length === 0 ? (
                  <div className="empty-state-small">
                    <FiFileText />
                    <p>생성된 문서가 없습니다.</p>
                  </div>
                ) : (
                  <div className="document-items">
                    {documents.map((doc) => (
                      <div
                        key={doc.document_id}
                        className={`document-item ${
                          selectedDocument?.document_id === doc.document_id ? 'active' : ''
                        }`}
                      >
                        <div
                          className="document-item-content"
                          onClick={() => handleViewDocument(selectedCaseId, doc.document_id)}
                        >
                          <FiFileText />
                          <div className="document-item-info">
                            <h4>{doc.title}</h4>
                            <span className="template-badge">{doc.template_used}</span>
                            <small>{new Date(doc.created_at).toLocaleString()}</small>
                          </div>
                        </div>
                        <button
                          className="btn-icon btn-danger"
                          onClick={() => handleDeleteDocument(selectedCaseId, doc.document_id)}
                          title="삭제"
                        >
                          <FiTrash2 />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* 문서 뷰어/에디터 */}
        <div className="document-viewer">
          {selectedDocument ? (
            <>
              <div className="viewer-header">
                <div>
                  <h3>{selectedDocument.title}</h3>
                  <span className="template-badge">{selectedDocument.template_used}</span>
                </div>
                <div className="viewer-actions">
                  <button className="btn-secondary" onClick={handleDownloadDocument}>
                    <FiDownload /> 다운로드
                  </button>
                  <button
                    className="btn-icon btn-danger"
                    onClick={() =>
                      selectedCaseId &&
                      handleDeleteDocument(selectedCaseId, selectedDocument.document_id)
                    }
                  >
                    <FiTrash2 /> 삭제
                  </button>
                </div>
              </div>
              <div className="viewer-content">
                <pre>{selectedDocument.content}</pre>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <FiEdit3 />
              <p>문서를 선택하면 내용을 확인할 수 있습니다.</p>
            </div>
          )}
        </div>
      </div>

      {/* 문서 생성 모달 */}
      {showGenerateModal && (
        <div className="modal-overlay" onClick={() => !isGenerating && handleCloseModal()}>
          <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
            <h3>AI 문서 생성</h3>
            <p>생성 방식을 선택하고 템플릿을 골라 문서를 작성하세요.</p>

            {/* 생성 방식 선택 */}
            <div className="generation-mode-section">
              <label className="section-label">🎯 생성 방식 선택</label>
              <div className="mode-options">
                <label className={`mode-option ${generationMode === 'quick' ? 'active' : ''}`}>
                  <input
                    type="radio"
                    name="generationMode"
                    value="quick"
                    checked={generationMode === 'quick'}
                    onChange={(e) => setGenerationMode(e.target.value as 'quick' | 'custom')}
                    disabled={isGenerating}
                  />
                  <div className="mode-content">
                    <div className="mode-title">⚡ 빠른 생성 (추천)</div>
                    <div className="mode-desc">AI가 사건 정보를 바탕으로 전체 문서를 자동 작성합니다</div>
                  </div>
                </label>
                <label className={`mode-option ${generationMode === 'custom' ? 'active' : ''}`}>
                  <input
                    type="radio"
                    name="generationMode"
                    value="custom"
                    checked={generationMode === 'custom'}
                    onChange={(e) => setGenerationMode(e.target.value as 'quick' | 'custom')}
                    disabled={isGenerating}
                  />
                  <div className="mode-content">
                    <div className="mode-title">✏️ 맞춤 생성</div>
                    <div className="mode-desc">핵심 정보를 입력하면 AI가 나머지를 채워넣습니다</div>
                  </div>
                </label>
              </div>
            </div>

            {/* 템플릿 선택 */}
            <div className="form-group">
              <label>📝 템플릿 선택</label>
              <select
                value={selectedTemplate}
                onChange={(e) => handleTemplateChange(e.target.value)}
                disabled={isGenerating}
              >
                <option value="">템플릿을 선택하세요</option>
                {allTemplates.map((template) => (
                  <option key={template} value={template}>
                    {template}
                  </option>
                ))}
              </select>
            </div>

            {/* 맞춤 생성 모드: 동적 입력 필드 */}
            {generationMode === 'custom' && selectedTemplate && TEMPLATE_FIELDS[selectedTemplate] && (
              <div className="custom-fields-section">
                <label className="section-label">✏️ 필수 입력 항목</label>
                {TEMPLATE_FIELDS[selectedTemplate].map((field) => (
                  <div key={field.name} className="form-group">
                    <label>
                      {field.label}
                      {field.required && <span className="required-mark">*</span>}
                    </label>
                    {field.type === 'textarea' ? (
                      <textarea
                        placeholder={field.placeholder}
                        value={customFields[field.name] || ''}
                        onChange={(e) => handleCustomFieldChange(field.name, e.target.value)}
                        disabled={isGenerating}
                        rows={3}
                      />
                    ) : (
                      <input
                        type={field.type}
                        placeholder={field.placeholder}
                        value={customFields[field.name] || ''}
                        onChange={(e) => handleCustomFieldChange(field.name, e.target.value)}
                        disabled={isGenerating}
                      />
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* 빠른 생성 모드: 추가 지시사항 */}
            {generationMode === 'quick' && (
              <div className="form-group">
                <label>💬 추가 지시사항 (선택)</label>
                <textarea
                  placeholder="문서 생성 시 특별히 강조하거나 추가할 내용이 있다면 입력하세요..."
                  value={userInstructions}
                  onChange={(e) => setUserInstructions(e.target.value)}
                  disabled={isGenerating}
                  rows={3}
                />
              </div>
            )}

            {generateError && (
              <div className="error-message">
                <FiAlertCircle />
                <span>{generateError}</span>
              </div>
            )}

            <div className="modal-actions">
              <button
                className="btn-secondary"
                onClick={handleCloseModal}
                disabled={isGenerating}
              >
                취소
              </button>
              <button
                className="btn-primary"
                onClick={handleGenerateDocument}
                disabled={isGenerating || !selectedTemplate}
              >
                {isGenerating ? (
                  <>
                    <FiLoader className="spinner" /> 생성 중...
                  </>
                ) : (
                  <>
                    <FiCpu /> 문서 생성
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentEditor;