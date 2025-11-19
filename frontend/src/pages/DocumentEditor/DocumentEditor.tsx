import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FiFileText, FiEdit3, FiCpu, FiDownload, FiTrash2, FiFolder, FiAlertCircle, FiLoader, FiStar, FiCheckCircle, FiX, FiEye } from 'react-icons/fi';
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

// 공통 필드 정의 (모든 템플릿에 필요)
const COMMON_FIELDS: TemplateField[] = [
  { name: 'case_name', label: '사건명', type: 'text', placeholder: '예: 대여금 청구의 건', required: true },
  { name: 'plaintiff_name', label: '원고/고소인 성명', type: 'text', placeholder: '홍길동', required: true },
  { name: 'plaintiff_address', label: '원고/고소인 주소', type: 'text', placeholder: '서울시 강남구 테헤란로 123', required: false },
  { name: 'defendant_name', label: '피고/피고소인 성명', type: 'text', placeholder: '임꺽정', required: true },
  { name: 'defendant_address', label: '피고/피고소인 주소', type: 'text', placeholder: '서울시 마포구 월드컵로 456', required: false },
];

// 핵심 6개 템플릿 필드 정의
const TEMPLATE_FIELDS: Record<string, TemplateField[]> = {
  '소장': [
    ...COMMON_FIELDS,
    { name: 'claim_amount', label: '청구 금액', type: 'number', placeholder: '예: 50000000', required: true },
    { name: 'claim_purpose', label: '청구 취지', type: 'textarea', placeholder: '피고는 원고에게 금 ○○원을 지급하라', required: true },
    { name: 'case_summary', label: '사건 개요', type: 'textarea', placeholder: '계약 체결 경위 및 채무 불이행 사실', required: false },
  ],
  '답변서': [
    ...COMMON_FIELDS,
    { name: 'admission', label: '인정 사항', type: 'textarea', placeholder: '원고 주장 중 인정하는 부분', required: false },
    { name: 'denial', label: '부인 사항', type: 'textarea', placeholder: '원고 주장 중 부인하는 부분과 이유', required: true },
    { name: 'defense', label: '항변 내용', type: 'textarea', placeholder: '소멸시효, 상계 등', required: false },
  ],
  '고소장': [
    ...COMMON_FIELDS,
    { name: 'crime_type', label: '죄명', type: 'text', placeholder: '예: 사기, 횡령, 절도', required: true },
    { name: 'crime_fact', label: '범죄 사실', type: 'textarea', placeholder: '육하원칙에 따른 범죄 사실 기술', required: true },
    { name: 'evidence_summary', label: '증거 개요', type: 'textarea', placeholder: '제출 증거 목록 및 설명', required: false },
  ],
  '변론요지서': [
    ...COMMON_FIELDS,
    { name: 'defense_argument', label: '변론 요지', type: 'textarea', placeholder: '무죄 주장 근거 또는 정상 참작 사유', required: true },
    { name: 'evidence_critique', label: '검사 증거 반박', type: 'textarea', placeholder: '검사 측 증거의 문제점', required: false },
  ],
  '내용증명': [
    ...COMMON_FIELDS,
    { name: 'debt_amount', label: '채무 금액', type: 'number', placeholder: '예: 10000000', required: true },
    { name: 'deadline', label: '이행 기한', type: 'text', placeholder: '예: 7일 이내', required: true },
    { name: 'legal_action', label: '불이행 시 조치', type: 'text', placeholder: '예: 민사소송 제기', required: false },
  ],
  '손해배상청구서': [
    ...COMMON_FIELDS,
    { name: 'accident_date', label: '사고 발생일', type: 'date', placeholder: '', required: true },
    { name: 'accident_location', label: '사고 장소', type: 'text', placeholder: '예: 서울시 강남구 테헤란로', required: true },
    { name: 'damages_amount', label: '총 손해액', type: 'number', placeholder: '예: 5000000', required: true },
    { name: 'damages_breakdown', label: '손해 내역', type: 'textarea', placeholder: '치료비, 휴업손해, 위자료 등 상세 내역', required: true },
  ],
  '근로계약서': [
    { name: 'contract_start_date', label: '계약 시작일', type: 'date', placeholder: '', required: true },
    { name: 'contract_end_date', label: '계약 종료일', type: 'date', placeholder: '', required: true },
    { name: 'employee_name', label: '근로자 성명', type: 'text', placeholder: '홍길동', required: true },
    { name: 'employee_id', label: '근로자 주민등록번호', type: 'text', placeholder: '123456-1234567', required: true },
    { name: 'employee_address', label: '근로자 주소', type: 'text', placeholder: '서울시 강남구 테헤란로 123', required: true },
    { name: 'employer_company', label: '사용자 상호', type: 'text', placeholder: '주식회사 ABC', required: true },
    { name: 'employer_name', label: '사용자 대표자명', type: 'text', placeholder: '김대표', required: true },
    { name: 'employer_business_number', label: '사용자 사업자번호', type: 'text', placeholder: '123-45-67890', required: true },
    { name: 'employer_address', label: '사용자 소재지', type: 'text', placeholder: '서울시 강남구 테헤란로 456', required: true },
    { name: 'workplace', label: '근무장소', type: 'text', placeholder: '서울시 강남구 테헤란로 456', required: true },
    { name: 'job_description', label: '업무내용', type: 'textarea', placeholder: '영업 및 마케팅 업무', required: true },
    { name: 'monthly_salary', label: '월 급여 (원)', type: 'number', placeholder: '3000000', required: true },
    { name: 'work_start_time', label: '근무 시작시간', type: 'text', placeholder: '09:00', required: false },
    { name: 'work_end_time', label: '근무 종료시간', type: 'text', placeholder: '18:00', required: false },
    { name: 'additional_terms', label: '특약사항', type: 'textarea', placeholder: '특별히 합의한 사항', required: false },
  ],
  '임대차계약서': [
    { name: 'property_address', label: '부동산 소재지', type: 'text', placeholder: '서울시 강남구 테헤란로 123, 456호', required: true },
    { name: 'property_type', label: '건물 종류', type: 'text', placeholder: '아파트', required: true },
    { name: 'property_area', label: '면적', type: 'text', placeholder: '84㎡', required: true },
    { name: 'landlord_name', label: '임대인 성명', type: 'text', placeholder: '김임대', required: true },
    { name: 'landlord_id', label: '임대인 주민번호', type: 'text', placeholder: '123456-1234567', required: true },
    { name: 'landlord_address', label: '임대인 주소', type: 'text', placeholder: '서울시 강남구', required: true },
    { name: 'landlord_phone', label: '임대인 연락처', type: 'text', placeholder: '010-1234-5678', required: true },
    { name: 'tenant_name', label: '임차인 성명', type: 'text', placeholder: '이임차', required: true },
    { name: 'tenant_id', label: '임차인 주민번호', type: 'text', placeholder: '234567-2345678', required: true },
    { name: 'tenant_address', label: '임차인 주소', type: 'text', placeholder: '서울시 마포구', required: true },
    { name: 'tenant_phone', label: '임차인 연락처', type: 'text', placeholder: '010-2345-6789', required: true },
    { name: 'contract_start_date', label: '임대차 시작일', type: 'date', placeholder: '', required: true },
    { name: 'contract_end_date', label: '임대차 종료일', type: 'date', placeholder: '', required: true },
    { name: 'deposit_amount', label: '보증금 (원)', type: 'number', placeholder: '100000000', required: true },
    { name: 'monthly_rent', label: '월 차임 (원)', type: 'number', placeholder: '0', required: false },
    { name: 'down_payment', label: '계약금 (원)', type: 'number', placeholder: '10000000', required: false },
    { name: 'additional_terms', label: '특약사항', type: 'textarea', placeholder: '특별히 합의한 사항', required: false },
  ],
  '업무위탁계약서': [
    { name: 'client_name', label: '위탁자 상호/성명', type: 'text', placeholder: '주식회사 ABC', required: true },
    { name: 'client_representative', label: '위탁자 대표자', type: 'text', placeholder: '김대표', required: true },
    { name: 'client_business_number', label: '위탁자 사업자번호', type: 'text', placeholder: '123-45-67890', required: false },
    { name: 'client_address', label: '위탁자 주소', type: 'text', placeholder: '서울시 강남구', required: true },
    { name: 'client_phone', label: '위탁자 연락처', type: 'text', placeholder: '02-1234-5678', required: true },
    { name: 'contractor_name', label: '수탁자 상호/성명', type: 'text', placeholder: '개인사업자 홍길동', required: true },
    { name: 'contractor_representative', label: '수탁자 대표자', type: 'text', placeholder: '홍길동', required: true },
    { name: 'contractor_business_number', label: '수탁자 사업자번호', type: 'text', placeholder: '234-56-78901', required: false },
    { name: 'contractor_address', label: '수탁자 주소', type: 'text', placeholder: '서울시 마포구', required: true },
    { name: 'contractor_phone', label: '수탁자 연락처', type: 'text', placeholder: '010-1234-5678', required: true },
    { name: 'contract_start_date', label: '계약 시작일', type: 'date', placeholder: '', required: true },
    { name: 'contract_end_date', label: '계약 종료일', type: 'date', placeholder: '', required: true },
    { name: 'service_description', label: '위탁업무 설명', type: 'textarea', placeholder: '웹사이트 개발 및 유지보수 업무', required: true },
    { name: 'work_scope', label: '업무 범위', type: 'textarea', placeholder: '상세한 업무 내용 기술', required: true },
    { name: 'total_fee', label: '총 위탁수수료 (원)', type: 'number', placeholder: '50000000', required: true },
    { name: 'payment_schedule', label: '지급 일정', type: 'text', placeholder: '착수금 30%, 중도금 30%, 잔금 40%', required: true },
    { name: 'additional_terms', label: '특약사항', type: 'textarea', placeholder: '특별히 합의한 사항', required: false },
  ],
  '매매계약서': [
    { name: 'property_address', label: '부동산 소재지', type: 'text', placeholder: '서울시 강남구 테헤란로 123', required: true },
    { name: 'property_area', label: '면적', type: 'text', placeholder: '대지 200㎡, 건물 150㎡', required: true },
    { name: 'land_category', label: '지목', type: 'text', placeholder: '대', required: false },
    { name: 'building_structure', label: '건물 구조', type: 'text', placeholder: '철근콘크리트조', required: false },
    { name: 'building_usage', label: '건물 용도', type: 'text', placeholder: '단독주택', required: false },
    { name: 'seller_name', label: '매도인 성명', type: 'text', placeholder: '김매도', required: true },
    { name: 'seller_id', label: '매도인 주민번호', type: 'text', placeholder: '123456-1234567', required: true },
    { name: 'seller_address', label: '매도인 주소', type: 'text', placeholder: '서울시 강남구', required: true },
    { name: 'seller_phone', label: '매도인 연락처', type: 'text', placeholder: '010-1234-5678', required: true },
    { name: 'buyer_name', label: '매수인 성명', type: 'text', placeholder: '이매수', required: true },
    { name: 'buyer_id', label: '매수인 주민번호', type: 'text', placeholder: '234567-2345678', required: true },
    { name: 'buyer_address', label: '매수인 주소', type: 'text', placeholder: '서울시 마포구', required: true },
    { name: 'buyer_phone', label: '매수인 연락처', type: 'text', placeholder: '010-2345-6789', required: true },
    { name: 'total_price', label: '총 매매대금 (원)', type: 'number', placeholder: '500000000', required: true },
    { name: 'down_payment', label: '계약금 (원)', type: 'number', placeholder: '50000000', required: true },
    { name: 'interim_payment', label: '중도금 (원)', type: 'number', placeholder: '200000000', required: false },
    { name: 'interim_payment_date', label: '중도금 지급일', type: 'date', placeholder: '', required: false },
    { name: 'balance_payment', label: '잔금 (원)', type: 'number', placeholder: '250000000', required: true },
    { name: 'balance_payment_date', label: '잔금 지급일', type: 'date', placeholder: '', required: true },
    { name: 'broker_name', label: '공인중개사 성명', type: 'text', placeholder: '박중개', required: false },
    { name: 'broker_office', label: '중개사무소명', type: 'text', placeholder: 'ABC부동산', required: false },
    { name: 'additional_terms', label: '특약사항', type: 'textarea', placeholder: '특별히 합의한 사항', required: false },
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

  // 미리보기 모달 상태
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewDocument, setPreviewDocument] = useState<DocumentDetail | null>(null);

  // 문서 상세보기 모달 상태
  const [showDocumentModal, setShowDocumentModal] = useState(false);
  const [modalDocument, setModalDocument] = useState<DocumentDetail | null>(null);

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
    if (!selectedTemplate) {
      setGenerateError('템플릿을 선택해주세요.');
      return;
    }

    // 사건이 없는 경우 빠른 생성 모드는 불가능
    if (!selectedCaseId && generationMode === 'quick') {
      setGenerateError('사건을 선택하지 않은 경우 맞춤 생성 모드만 사용할 수 있습니다.');
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
        ...(selectedCaseId && { case_id: selectedCaseId }),  // Only include if case is selected
        template_name: selectedTemplate,
        generation_mode: generationMode,
        custom_fields: generationMode === 'custom' ? customFields : undefined,
        user_instructions: userInstructions || undefined,
      });

      // 사건 기반 문서인 경우에만 문서 목록 새로고침
      if (selectedCaseId) {
        await loadDocuments(selectedCaseId);
      }

      // 미리보기 모달 표시
      setPreviewDocument(document);
      setShowPreviewModal(true);

      // 입력 모달 닫기
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

  const handleViewDocumentModal = async (caseId: string, documentId: string) => {
    try {
      const document: DocumentDetail = await apiClient.getDocument(caseId, documentId);
      setModalDocument(document);
      setShowDocumentModal(true);
    } catch (error) {
      console.error('Error loading document for modal:', error);
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

  // 미리보기에서 다운로드
  const handlePreviewDownload = () => {
    if (!previewDocument) return;

    const blob = new Blob([previewDocument.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${previewDocument.title}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // 미리보기 모달 닫기 및 저장
  const handlePreviewClose = () => {
    if (previewDocument) {
      setSelectedDocument(previewDocument);
    }
    setShowPreviewModal(false);
    setPreviewDocument(null);
  };

  // 미리보기 모달 저장 없이 닫기
  const handlePreviewDismiss = () => {
    setShowPreviewModal(false);
    setPreviewDocument(null);
  };

  // 미리보기에서 다시 생성
  const handlePreviewRegenerate = () => {
    setShowPreviewModal(false);
    setPreviewDocument(null);
    setShowGenerateModal(true);
    // 기존 입력값 유지됨
  };

  // 모달 열기 (사건 선택 여부와 관계없이 가능)
  const handleOpenModal = () => {
    // 사건이 선택되지 않은 경우 자동으로 맞춤 생성 모드로 설정
    if (!selectedCaseId) {
      setGenerationMode('custom');
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

  // 모든 템플릿 목록 (TEMPLATE_FIELDS에서 직접 추출)
  const allTemplates = Object.keys(TEMPLATE_FIELDS);

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
                        <div className="document-item-actions">
                          <button
                            className="btn-icon-view"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleViewDocumentModal(selectedCaseId, doc.document_id);
                            }}
                            title="상세보기"
                          >
                            <FiEye />
                          </button>
                          <button
                            className="btn-icon-delete"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteDocument(selectedCaseId, doc.document_id);
                            }}
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
                  <button
                    className="btn-icon-only btn-download"
                    onClick={handleDownloadDocument}
                    title="다운로드"
                  >
                    <FiDownload />
                  </button>
                  <button
                    className="btn-icon-only btn-delete"
                    onClick={() =>
                      selectedCaseId &&
                      handleDeleteDocument(selectedCaseId, selectedDocument.document_id)
                    }
                    title="삭제"
                  >
                    <FiTrash2 />
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
            <div className="modal-header">
              <h3>AI 문서 생성</h3>
              <p>생성 방식을 선택하고 템플릿을 골라 문서를 작성하세요.</p>
            </div>

            <div className="modal-body">
              {/* 사건 미선택 시 안내 메시지 */}
              {!selectedCaseId && (
                <div className="scenario-info" style={{marginBottom: '16px'}}>
                  ℹ️ 사건을 선택하지 않았습니다. 맞춤 생성 모드로 직접 정보를 입력하여 문서를 생성할 수 있습니다.
                </div>
              )}

            {/* 생성 방식 선택 */}
            <div className="generation-mode-section">
              <label className="section-label">🎯 생성 방식 선택</label>
              <div className="mode-options">
                <label className={`mode-option ${generationMode === 'quick' ? 'active' : ''} ${!selectedCaseId ? 'disabled' : ''}`}>
                  <input
                    type="radio"
                    name="generationMode"
                    value="quick"
                    checked={generationMode === 'quick'}
                    onChange={(e) => setGenerationMode(e.target.value as 'quick' | 'custom')}
                    disabled={isGenerating || !selectedCaseId}
                  />
                  <div className="mode-content">
                    <div className="mode-title">⚡ 빠른 생성 {selectedCaseId && '(추천)'}</div>
                    <div className="mode-desc">
                      {selectedCaseId
                        ? 'AI가 사건 정보를 바탕으로 전체 문서를 자동 작성합니다'
                        : '사건 선택 필요 - 사건 분석 정보를 기반으로 문서를 생성합니다'}
                    </div>
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
                    <div className="mode-title">✏️ 맞춤 생성 {!selectedCaseId && '(독립 모드)'}</div>
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
            </div>

            <div className="modal-footer">
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
        </div>
      )}

      {/* 미리보기 모달 */}
      {showPreviewModal && previewDocument && (
        <div className="modal-overlay" onClick={handlePreviewClose}>
          <div className="modal-content modal-preview" onClick={(e) => e.stopPropagation()}>
            <div className="preview-header">
              <div>
                <h3>{previewDocument.title}</h3>
                <span className="template-badge">{previewDocument.template_used}</span>
              </div>
              <button
                className="preview-close-btn"
                onClick={handlePreviewDismiss}
                title="닫기"
              >
                <FiX />
              </button>
            </div>

            <div className="preview-content-wrapper">
              <pre className="preview-content">{previewDocument.content}</pre>
            </div>

            <div className="preview-actions">
              <button
                className="btn-secondary"
                onClick={handlePreviewRegenerate}
              >
                <FiEdit3 /> 다시 생성
              </button>
              <button
                className="btn-primary"
                onClick={handlePreviewDownload}
              >
                <FiDownload /> 다운로드
              </button>
              <button
                className="btn-primary"
                onClick={handlePreviewClose}
              >
                <FiFileText /> 저장하고 닫기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 문서 상세보기 모달 */}
      {showDocumentModal && modalDocument && (
        <div className="modal-overlay" onClick={() => setShowDocumentModal(false)}>
          <div className="modal-content modal-preview" onClick={(e) => e.stopPropagation()}>
            <div className="preview-header">
              <div>
                <h3>{modalDocument.title}</h3>
                <span className="template-badge">{modalDocument.template_used}</span>
              </div>
              <button
                className="preview-close-btn"
                onClick={() => setShowDocumentModal(false)}
                title="닫기"
              >
                <FiX />
              </button>
            </div>

            <div className="preview-content-wrapper">
              <pre className="preview-content">{modalDocument.content}</pre>
            </div>

            <div className="preview-actions">
              <button
                className="btn-primary"
                onClick={() => {
                  const blob = new Blob([modalDocument.content], { type: 'text/plain;charset=utf-8' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `${modalDocument.title}.txt`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  URL.revokeObjectURL(url);
                }}
              >
                <FiDownload /> 다운로드
              </button>
              <button
                className="btn-secondary"
                onClick={() => setShowDocumentModal(false)}
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentEditor;