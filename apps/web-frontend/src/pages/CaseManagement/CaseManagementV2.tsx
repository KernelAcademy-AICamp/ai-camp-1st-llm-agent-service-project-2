import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FiFolder,
  FiUpload,
  FiPlus,
  FiFileText,
  FiTrash2,
  FiEye,
  FiAlertCircle,
  FiCpu,
  FiLoader,
  FiShield,
  FiMessageCircle,
  FiDollarSign,
  FiHeart,
  FiMic,
  FiCamera,
  FiClipboard,
  FiBook,
  FiFile,
  FiCheck,
  FiClock
} from 'react-icons/fi';
import apiClient from '../../api/client';
import {
  CriminalCaseAnalysis,
  CriminalCaseListItem,
  CriminalStage,
  CriminalAnalysisStatus
} from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import OCRReviewModal, { ExtractionResult } from '../../components/OCRReviewModal/OCRReviewModal';
import './CaseManagementV2.css';

// 문서 카테고리 타입 (일반인 친화적으로 확장)
type DocumentCategory =
  | 'chat_evidence'      // 대화 증거
  | 'financial_evidence' // 금전 증거
  | 'medical_evidence'   // 의료 증거
  | 'recording_evidence' // 녹취/영상
  | 'screenshot_evidence'// 스크린샷
  | 'police_document'    // 경찰 서류
  | 'court_document'     // 법원 서류
  | 'other';

// 문서 카테고리 옵션 (세련된 아이콘 사용)
const DOCUMENT_CATEGORIES: { value: DocumentCategory; label: string; icon: React.ReactNode; description?: string }[] = [
  { value: 'chat_evidence', label: '대화 증거', icon: <FiMessageCircle />, description: '카카오톡, 문자, SNS 대화' },
  { value: 'financial_evidence', label: '금전 증거', icon: <FiDollarSign />, description: '계좌이체 내역, 영수증' },
  { value: 'medical_evidence', label: '진단서·의료기록', icon: <FiHeart />, description: '병원 진단서, 치료 기록' },
  { value: 'recording_evidence', label: '녹취록·영상', icon: <FiMic />, description: '녹음 파일, CCTV 영상' },
  { value: 'screenshot_evidence', label: '스크린샷·캡처', icon: <FiCamera />, description: '게시글 캡처, 화면 저장' },
  { value: 'police_document', label: '경찰 서류', icon: <FiClipboard />, description: '출석요구서, 고소장, 조서' },
  { value: 'court_document', label: '법원 서류', icon: <FiBook />, description: '기소장, 판결문, 결정문' },
  { value: 'other', label: '기타', icon: <FiFile />, description: '위 항목에 해당하지 않는 문서' },
];

// 형사 절차 단계 라벨
const STAGE_LABELS: Record<CriminalStage, string> = {
  COMPLAINT: '고소/고발',
  INVESTIGATION: '수사 중',
  PROSECUTION: '기소',
  TRIAL: '재판 중',
  JUDGMENT: '선고',
  CLOSED: '종결',
};

// 형사 절차 단계 색상
const STAGE_COLORS: Record<CriminalStage, string> = {
  COMPLAINT: '#f59e0b',
  INVESTIGATION: '#3b82f6',
  PROSECUTION: '#1e40af',
  TRIAL: '#ec4899',
  JUDGMENT: '#10b981',
  CLOSED: '#6b7280',
};

// 분석 중인 사건 정보를 저장하는 타입
interface AnalyzingCase {
  tempId: string;
  files: File[];
  documentCategory: DocumentCategory;
  startTime: number;
}

// OCR이 필요한 파일 확장자
const OCR_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp'];

const CaseManagementV2: React.FC = () => {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [cases, setCases] = useState<CriminalCaseListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false); // 로딩 상태 추가
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [documentCategory, setDocumentCategory] = useState<DocumentCategory>('other');
  // 카테고리 선택 영역 ref (자동 스크롤용)
  const categorySectionRef = useRef<HTMLDivElement>(null);
  // 분석 중인 사건들을 추적 (tempId -> AnalyzingCase)
  const analyzingCasesRef = useRef<Map<string, AnalyzingCase>>(new Map());
  // Race condition 방지를 위한 요청 ID 추적
  const loadRequestIdRef = useRef<number>(0);

  // OCR 관련 상태
  const [showOCRModal, setShowOCRModal] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionResult, setExtractionResult] = useState<ExtractionResult | null>(null);
  const [currentOCRFileIndex, setCurrentOCRFileIndex] = useState<number>(0);
  const [ocrQueue, setOcrQueue] = useState<File[]>([]); // OCR이 필요한 파일들의 큐
  const [confirmedTexts, setConfirmedTexts] = useState<Map<string, string>>(new Map()); // 파일명 -> 확인된 텍스트

  // 사건 목록 로드 (useCallback으로 메모이제이션 + Race condition 방지)
  const loadCases = useCallback(async () => {
    if (!token) return;

    // 현재 요청 ID 저장 (Race condition 방지)
    const currentRequestId = ++loadRequestIdRef.current;

    setIsLoading(true);
    try {
      const data = await apiClient.getCriminalCases(token);

      // 최신 요청이 아니면 무시 (Race condition 방지)
      if (currentRequestId !== loadRequestIdRef.current) {
        console.log('[loadCases] Stale response ignored');
        return;
      }

      console.log('[loadCases] API response:', data);
      // API 응답이 배열인지 객체인지 확인
      const casesArray = Array.isArray(data) ? data : (data?.cases || []);
      console.log('[loadCases] casesArray:', casesArray);
      if (casesArray.length > 0) {
        console.log('[loadCases] First case:', casesArray[0]);
        console.log('[loadCases] First case case_id:', casesArray[0].case_id);
      }

      // 분석 중인 임시 케이스를 유지하면서 서버 데이터 병합
      setCases(prev => {
        const tempCases = prev.filter(c => c.case_id?.startsWith('temp_'));
        const serverCaseIds = new Set(casesArray.map((c: CriminalCaseListItem) => c.case_id));
        // 서버에 아직 없는 임시 케이스만 유지
        const validTempCases = tempCases.filter(tc => !serverCaseIds.has(tc.case_id));
        return [...validTempCases, ...casesArray];
      });
    } catch (error) {
      // 최신 요청이 아니면 무시
      if (currentRequestId !== loadRequestIdRef.current) return;

      console.error('Error loading criminal cases:', error);
      // 폴백: 일반 케이스 API 시도
      try {
        const fallbackData = await apiClient.getCases(token);

        // 다시 최신 요청 체크
        if (currentRequestId !== loadRequestIdRef.current) return;

        // API 응답이 배열인지 객체인지 확인
        const fallbackArray = Array.isArray(fallbackData)
          ? fallbackData
          : (fallbackData?.cases || (fallbackData as any)?.results || []);

        setCases(prev => {
          const tempCases = prev.filter(c => c.case_id?.startsWith('temp_'));
          return [...tempCases, ...fallbackArray];
        });
      } catch (fallbackError) {
        if (currentRequestId !== loadRequestIdRef.current) return;
        console.error('Fallback also failed:', fallbackError);
        // 에러 시에도 임시 케이스는 유지
        setCases(prev => prev.filter(c => c.case_id?.startsWith('temp_')));
      }
    } finally {
      if (currentRequestId === loadRequestIdRef.current) {
        setIsLoading(false);
      }
    }
  }, [token]);

  // 사건 목록 로드 (토큰이 있을 때만)
  useEffect(() => {
    loadCases();
  }, [loadCases]);

  // OCR이 필요한 파일인지 확인하는 헬퍼 함수
  const isOCRFile = (file: File): boolean => {
    const extension = file.name.split('.').pop()?.toLowerCase();
    return extension ? OCR_EXTENSIONS.includes(extension) : false;
  };

  // OCR 추출 시작
  const triggerExtraction = async (file: File) => {
    setIsExtracting(true);
    setShowOCRModal(true);
    setExtractionResult(null);

    try {
      const response = await apiClient.extractDocumentText(file);

      if (!response.success) {
        throw new Error(response.error || '텍스트 추출 실패');
      }

      const result: ExtractionResult = {
        success: response.success,
        text: response.text,
        extraction_method: response.extraction_method,
        needs_review: response.needs_review,
        confidence: response.confidence,
        file_type: response.file_type,
        metadata: response.metadata,
        error: response.error,
      };
      setExtractionResult(result);
    } catch (err: any) {
      setUploadError(err.message || '텍스트 추출 실패');
      setShowOCRModal(false);
      // 추출 실패 시 다음 파일로 진행
      processNextOCRFile();
    } finally {
      setIsExtracting(false);
    }
  };

  // OCR 큐에서 다음 파일 처리
  const processNextOCRFile = useCallback(() => {
    const nextIndex = currentOCRFileIndex + 1;
    if (nextIndex < ocrQueue.length) {
      setCurrentOCRFileIndex(nextIndex);
      triggerExtraction(ocrQueue[nextIndex]);
    } else {
      // 모든 OCR 파일 처리 완료 - 카테고리 선택으로 이동
      setOcrQueue([]);
      setCurrentOCRFileIndex(0);
      setTimeout(() => {
        categorySectionRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }, 100);
    }
  }, [currentOCRFileIndex, ocrQueue]);

  // OCR 확인 핸들러
  const handleOCRConfirm = (text: string) => {
    const currentFile = ocrQueue[currentOCRFileIndex];
    if (currentFile) {
      // 확인된 텍스트 저장
      setConfirmedTexts(prev => {
        const newMap = new Map(prev);
        newMap.set(currentFile.name, text);
        return newMap;
      });
    }
    setShowOCRModal(false);
    setExtractionResult(null);
    // 다음 파일 처리
    processNextOCRFile();
  };

  // OCR 취소 핸들러
  const handleOCRCancel = () => {
    setShowOCRModal(false);
    setExtractionResult(null);
    // 취소해도 다음 파일로 계속 진행 (사용자가 원하면 텍스트 없이 진행)
    processNextOCRFile();
  };

  // 파일 선택 핸들러
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(files);
    setUploadError(null);
    setConfirmedTexts(new Map()); // 기존 확인 텍스트 초기화

    // OCR이 필요한 파일 필터링
    const ocrFiles = files.filter(isOCRFile);

    if (ocrFiles.length > 0) {
      // OCR이 필요한 파일이 있으면 OCR 프로세스 시작
      setOcrQueue(ocrFiles);
      setCurrentOCRFileIndex(0);
      triggerExtraction(ocrFiles[0]);
    } else if (files.length > 0) {
      // OCR이 필요 없는 파일만 있으면 바로 카테고리 선택으로 이동
      setTimeout(() => {
        categorySectionRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }, 100);
    }
  };

  // 파일 업로드 및 분석 (비동기 패턴 - 즉시 상세 페이지로 이동)
  const handleUploadFiles = useCallback(async () => {
    if (selectedFiles.length === 0) {
      setUploadError('파일을 선택해주세요.');
      return;
    }

    // 1. 임시 ID 생성
    const tempId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // 2. 임시 사건 정보 생성
    const tempCase: CriminalCaseListItem = {
      case_id: tempId,
      case_name: selectedFiles.map(f => f.name).join(', '),
      summary: 'AI가 문서를 분석하고 있습니다...',
      document_count: selectedFiles.length,
      crime_type: documentCategory !== 'other' ?
        DOCUMENT_CATEGORIES.find(c => c.value === documentCategory)?.label : undefined,
      created_at: Date.now() / 1000,
      analysis_status: 'analyzing',
    };

    // 3. 분석 중인 사건 정보를 localStorage에 저장 (상세 페이지에서 접근 가능)
    const analyzingInfo = {
      tempId,
      tempCase,
      files: selectedFiles.map(f => ({ name: f.name, size: f.size })),
      documentCategory,
      startTime: Date.now(),
    };
    localStorage.setItem(`analyzing_case_${tempId}`, JSON.stringify(analyzingInfo));

    // 4. 목록에 임시 사건 추가
    setCases(prev => [tempCase, ...prev]);

    // 5. 분석 중인 사건 정보 저장
    analyzingCasesRef.current.set(tempId, {
      tempId,
      files: [...selectedFiles],
      documentCategory,
      startTime: Date.now(),
    });

    // 5-1. confirmedTexts를 Object로 변환 (API 전달용)
    const confirmedTextsObj: Record<string, string> = {};
    confirmedTexts.forEach((text, fileName) => {
      confirmedTextsObj[fileName] = text;
    });

    // 6. 모달 닫고 상태 초기화
    setShowUploadModal(false);
    setSelectedFiles([]);
    setDocumentCategory('other');
    setUploadError(null);
    setConfirmedTexts(new Map()); // OCR 텍스트도 초기화

    // 7. 즉시 상세 페이지로 이동 (분석 완료를 기다리지 않음)
    navigate(`/cases-v2/${tempId}`);

    // 8. 백그라운드에서 실제 API 호출 (단계별 진행 상태 업데이트)
    try {
      // 단계 업데이트 헬퍼 함수
      const updateStage = (stage: string, progress: number, stageLabel?: string) => {
        const stored = localStorage.getItem(`analyzing_case_${tempId}`);
        if (stored) {
          const info = JSON.parse(stored);
          info.stage = stage;
          info.progress = progress;
          info.stageLabel = stageLabel;
          info.stageUpdatedAt = Date.now();
          localStorage.setItem(`analyzing_case_${tempId}`, JSON.stringify(info));
        }
      };

      // 단계 1: 파일 업로드 시작 (5%)
      updateStage('uploading', 5, '파일 업로드 중...');

      // 단계 2: API 호출 시작 - 업로드 진행 (30%)
      updateStage('uploading', 30, '서버로 전송 중...');

      const analysis: CriminalCaseAnalysis = await apiClient.uploadCriminalCaseFiles(
        analyzingCasesRef.current.get(tempId)?.files || [],
        analyzingCasesRef.current.get(tempId)?.documentCategory || 'other',
        token || undefined,
        confirmedTextsObj // OCR로 추출된 텍스트 전달
      );

      // API 응답 받음 = 분석 완료 (서버에서 모든 처리가 끝남)

      // 9. 분석 완료 - localStorage에 결과 저장 (상세 페이지에서 폴링)
      const completedInfo = {
        tempId,
        realCaseId: analysis.case_id,
        analysis,
        status: 'completed' as const,
        completedAt: Date.now(),
      };
      localStorage.setItem(`analyzing_case_${tempId}`, JSON.stringify(completedInfo));

      // 10. 목록 업데이트
      setCases(prev => prev.map(c =>
        c.case_id === tempId
          ? {
              case_id: analysis.case_id,
              case_name: analysis.suggested_case_name || analysis.case_name || '새 사건',
              summary: analysis.summary,
              document_count: analysis.uploaded_files?.length || 0,
              crime_type: analysis.crime_type,
              created_at: Date.now() / 1000,
              analysis_status: 'completed' as CriminalAnalysisStatus,
            }
          : c
      ));

      analyzingCasesRef.current.delete(tempId);

    } catch (error: any) {
      console.error('Criminal case analysis failed:', error);

      // 폴백: 기본 업로드 시도
      try {
        const fallbackAnalysis = await apiClient.uploadCaseFiles(
          analyzingCasesRef.current.get(tempId)?.files || [],
          token || undefined
        );

        const completedInfo = {
          tempId,
          realCaseId: fallbackAnalysis.case_id,
          analysis: fallbackAnalysis,
          status: 'completed' as const,
          completedAt: Date.now(),
        };
        localStorage.setItem(`analyzing_case_${tempId}`, JSON.stringify(completedInfo));

        setCases(prev => prev.map(c =>
          c.case_id === tempId
            ? {
                case_id: fallbackAnalysis.case_id,
                case_name: (fallbackAnalysis as any).case_name || (fallbackAnalysis as any).suggested_case_name || '새 사건',
                summary: fallbackAnalysis.summary,
                document_count: fallbackAnalysis.uploaded_files?.length || 0,
                created_at: Date.now() / 1000,
                analysis_status: 'completed' as CriminalAnalysisStatus,
              }
            : c
        ));

        analyzingCasesRef.current.delete(tempId);

      } catch (fallbackError: any) {
        // 분석 실패 - localStorage에 실패 상태 저장
        const failedInfo = {
          tempId,
          status: 'failed' as const,
          error: fallbackError.message || '알 수 없는 오류',
          failedAt: Date.now(),
        };
        localStorage.setItem(`analyzing_case_${tempId}`, JSON.stringify(failedInfo));

        setCases(prev => prev.map(c =>
          c.case_id === tempId
            ? { ...c, analysis_status: 'failed' as CriminalAnalysisStatus, summary: '분석 실패: ' + (fallbackError.message || '알 수 없는 오류') }
            : c
        ));

        analyzingCasesRef.current.delete(tempId);
      }
    }
  }, [selectedFiles, documentCategory, token, navigate]);

  // 사건 상세 페이지로 이동
  const handleViewCase = (caseId: string) => {
    console.log('[handleViewCase] caseId:', caseId, 'type:', typeof caseId);
    // 분석 중인 임시 사건이거나 유효하지 않은 caseId는 이동하지 않음
    if (!caseId || caseId.startsWith('temp_') || caseId === 'null' || caseId === 'undefined') {
      console.log('[handleViewCase] Blocked navigation - invalid caseId');
      return;
    }
    console.log('[handleViewCase] Navigating to:', `/cases-v2/${caseId}`);
    navigate(`/cases-v2/${caseId}`);
  };

  // 사건 삭제
  const handleDeleteCase = async (caseId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // 이벤트 전파 방지
    if (!window.confirm('정말로 이 사건을 삭제하시겠습니까?')) return;

    try {
      await apiClient.deleteCriminalCase(caseId, token || undefined);
      // 사건 목록 새로고침
      await loadCases();
    } catch (error) {
      // 폴백
      try {
        await apiClient.deleteCase(caseId, token || undefined);
        await loadCases();
      } catch (fallbackError) {
        console.error('Error deleting case:', fallbackError);
        alert('사건 삭제 중 오류가 발생했습니다.');
      }
    }
  };

  return (
    <div className="case-management-v2 list-only">
      <div className="page-header">
        <div>
          <h2>
            <FiShield className="header-icon" />
            형사 사건 관리
          </h2>
          <p>증거 자료를 업로드하고 AI가 분석한 결과를 확인하세요</p>
        </div>
        <div className="header-actions">
          <button className="btn-primary" onClick={() => setShowUploadModal(true)}>
            <FiPlus /> 새 사건 등록
          </button>
        </div>
      </div>

      <div className="case-list-container">
        <h3>형사 사건 목록 ({cases.length})</h3>
        {/* 로딩 상태 표시 */}
        {isLoading && cases.length === 0 ? (
          <div className="loading-state">
            <FiLoader className="spin" style={{ fontSize: '2rem', marginBottom: '1rem' }} />
            <p>사건 목록을 불러오는 중...</p>
          </div>
        ) : cases.length === 0 ? (
          <div className="empty-state-large">
            <FiFolder />
            <h4>아직 등록된 형사 사건이 없습니다</h4>
            <p>증거 자료를 업로드하면 AI가 분석하여 사건을 정리해 드립니다.</p>
            <button className="btn-primary" onClick={() => setShowUploadModal(true)}>
              <FiUpload /> 첫 사건 업로드하기
            </button>
          </div>
        ) : (
          <div className="case-grid">
            {cases.map((caseItem) => (
              <div
                key={caseItem.case_id}
                className={`case-card ${caseItem.analysis_status === 'analyzing' ? 'analyzing' : ''}`}
                onClick={() => handleViewCase(caseItem.case_id)}
              >
                <div className="case-card-header">
                  <FiFolder className="case-icon" />
                  <h4>{caseItem.case_name}</h4>
                  {/* 분석 상태 배지 */}
                  {caseItem.analysis_status && (
                    <span className={`analysis-status-badge ${caseItem.analysis_status}`}>
                      {caseItem.analysis_status === 'analyzing' && (
                        <>
                          <FiLoader className="spin" />
                          <span>분석 중</span>
                        </>
                      )}
                      {caseItem.analysis_status === 'completed' && (
                        <>
                          <FiCheck />
                          <span>완료</span>
                        </>
                      )}
                      {caseItem.analysis_status === 'failed' && (
                        <>
                          <FiAlertCircle />
                          <span>실패</span>
                        </>
                      )}
                      {caseItem.analysis_status === 'pending' && (
                        <>
                          <FiClock />
                          <span>대기</span>
                        </>
                      )}
                    </span>
                  )}
                </div>

                {/* 범죄 유형 및 단계 배지 */}
                <div className="case-card-badges">
                  {caseItem.crime_type && (
                    <span className="crime-type-badge">{caseItem.crime_type}</span>
                  )}
                  {caseItem.stage && (
                    <span
                      className="stage-badge"
                      style={{ backgroundColor: `${STAGE_COLORS[caseItem.stage]}20`, color: STAGE_COLORS[caseItem.stage] }}
                    >
                      {STAGE_LABELS[caseItem.stage]}
                    </span>
                  )}
                </div>

                <p className="case-card-summary">{caseItem.summary}</p>

                <div className="case-card-footer">
                  <span className="case-meta">{caseItem.document_count || 0}개 문서</span>
                  <span className="case-meta">{new Date(caseItem.created_at).toLocaleDateString('ko-KR')}</span>
                </div>

                {/* 분석 중이면 진행 표시 */}
                {caseItem.analysis_status === 'analyzing' && (
                  <div className="analyzing-overlay">
                    <div className="analyzing-spinner-small">
                      <FiCpu className="spin" />
                    </div>
                    <span>AI 분석 진행 중...</span>
                  </div>
                )}

                {/* 액션 버튼 */}
                {caseItem.analysis_status !== 'analyzing' && (
                  <div className="case-card-actions">
                    <button
                      className="btn-icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleViewCase(caseItem.case_id);
                      }}
                      title="상세 보기"
                    >
                      <FiEye />
                    </button>
                    <button
                      className="btn-icon btn-danger"
                      onClick={(e) => handleDeleteCase(caseItem.case_id, e)}
                      title="삭제"
                    >
                      <FiTrash2 />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 파일 업로드 모달 */}
      {showUploadModal && (
        <div className="modal-overlay" onClick={() => !isUploading && setShowUploadModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>새 사건 등록</h3>
            <p>가지고 있는 증거 자료를 업로드하면 AI가 분석해 드립니다.</p>

            {/* Step 1: 파일 업로드 (먼저) */}
            <div className="upload-step">
              <div className="step-header">
                <span className="step-number">1</span>
                <span className="step-title">파일 선택</span>
              </div>
              <div className="file-upload-area">
                <input
                  type="file"
                  id="file-input"
                  multiple
                  accept=".pdf,.docx,.doc,.txt,.hwp,.png,.jpg,.jpeg,.gif,.bmp,.tiff,.webp,image/*"
                  onChange={handleFileSelect}
                  disabled={isUploading}
                />
                <label htmlFor="file-input" className="file-upload-label">
                  <FiUpload />
                  <span>파일 선택 (PDF, DOCX, TXT, HWP, 이미지)</span>
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
            </div>

            {/* Step 2: 문서 카테고리 선택 (파일 선택 후 스크롤) */}
            <div className="upload-step" ref={categorySectionRef}>
              <div className="step-header">
                <span className="step-number">2</span>
                <span className="step-title">자료 종류 선택</span>
              </div>
              <div className="document-category-select">
                <div className="category-grid">
                  {DOCUMENT_CATEGORIES.map((cat) => (
                    <button
                      key={cat.value}
                      type="button"
                      className={`category-btn ${documentCategory === cat.value ? 'active' : ''}`}
                      onClick={() => setDocumentCategory(cat.value)}
                      disabled={isUploading}
                    >
                      <span className="category-icon">{cat.icon}</span>
                      <span className="category-label">{cat.label}</span>
                      {cat.description && (
                        <span className="category-desc">{cat.description}</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
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
                <p className="upload-status">파일 업로드 및 AI 형사 분석 중...</p>
                <p className="upload-detail">
                  구성요건 분석, 양형인자 추출, 양형 예측, 관련 판례 검색 진행 중
                </p>
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
                {isUploading ? '분석 중...' : '업로드 및 형사 분석'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* OCR 검토 모달 */}
      {showOCRModal && (
        <OCRReviewModal
          isOpen={showOCRModal}
          onClose={handleOCRCancel}
          onConfirm={handleOCRConfirm}
          extractionResult={extractionResult}
          fileName={ocrQueue[currentOCRFileIndex]?.name || ''}
          isLoading={isExtracting}
        />
      )}
    </div>
  );
};

export default CaseManagementV2;
