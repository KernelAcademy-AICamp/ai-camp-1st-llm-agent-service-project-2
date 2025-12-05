import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  FiArrowLeft,
  FiFileText,
  FiTrash2,
  FiLoader,
  FiShield,
  FiUser,
  FiBriefcase,
  FiCpu,
  FiBook,
  FiEdit,
  FiX,
  FiSliders,
  FiTarget,
  FiList,
  FiArrowRight,
  FiAlertCircle,
  FiCheckCircle
} from 'react-icons/fi';
import apiClient from '../../api/client';
import { CriminalCaseAnalysis } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import { applyPartialMasking, maskKoreanName } from '../../utils/piiMasker';
// 전문가용 카드
import CrimeElementsCard from './components/CrimeElementsCard';
import SentencingFactorsCard from './components/SentencingFactorsCard';
import SentenceEstimateCard from './components/SentenceEstimateCard';
import DefenseStrategiesCard from './components/DefenseStrategiesCard';
import CriminalPrecedentCard from './components/CriminalPrecedentCard';
// 일반인용 카드
import PossibilityCard from './components/PossibilityCard';
import SimpleFactorsCard from './components/SimpleFactorsCard';
import NextStepsCard from './components/NextStepsCard';
import ExpectedResultCard from './components/ExpectedResultCard';
import './CaseDetailV2.css';

// localStorage에 저장된 분석 상태 타입
interface AnalyzingCaseInfo {
  tempId: string;
  tempCase?: {
    case_id: string;
    case_name: string;
    summary: string;
    document_count: number;
    crime_type?: string;
  };
  files?: Array<{ name: string; size: number }>;
  documentCategory?: string;
  startTime?: number;
  // 단계별 진행 상태
  stage?: 'uploading' | 'parsing' | 'analyzing' | 'searching' | 'finalizing' | 'completed';
  progress?: number;
  stageLabel?: string;
  stageUpdatedAt?: number;
  // 완료된 경우
  realCaseId?: string;
  analysis?: CriminalCaseAnalysis;
  status?: 'analyzing' | 'completed' | 'failed';
  completedAt?: number;
  error?: string;
  failedAt?: number;
}

// 뷰 모드 타입
type ViewMode = 'simple' | 'expert';

// 탭 타입
type TabType = 'summary' | 'elements' | 'sentencing' | 'precedents' | 'nextsteps';

// caseId 유효성 검사 헬퍼
const isValidCaseId = (id: string | undefined): id is string => {
  return !!id && id !== 'null' && id !== 'undefined' && id.trim() !== '';
};

// temp_ ID 여부 확인
const isTempCaseId = (id: string | undefined): boolean => {
  return !!id && id.startsWith('temp_');
};

const CaseDetailV2: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const { token } = useAuth();

  const [caseData, setCaseData] = useState<CriminalCaseAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('simple');
  const [activeTab, setActiveTab] = useState<TabType>('summary');
  const [showDocumentPanel, setShowDocumentPanel] = useState(false);

  // 분석 중 상태 관리
  const [analyzingInfo, setAnalyzingInfo] = useState<AnalyzingCaseInfo | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<'analyzing' | 'completed' | 'failed' | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [stageLabel, setStageLabel] = useState<string>('분석 준비 중...');
  const [currentStage, setCurrentStage] = useState<string>('uploading');
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 판례 검색 상태 관리 (비동기 처리)
  const [precedentsLoading, setPrecedentsLoading] = useState(false);
  const [precedentsStatus, setPrecedentsStatus] = useState<'pending' | 'searching' | 'completed' | 'failed'>('pending');
  const precedentsSearched = useRef(false); // 검색 중복 방지

  // temp_ ID가 아닌 무효한 caseId만 리다이렉트
  useEffect(() => {
    if (!isValidCaseId(caseId)) {
      console.warn('Invalid caseId detected:', caseId);
      navigate('/cases-v2', { replace: true });
    }
  }, [caseId, navigate]);

  // localStorage 폴링으로 분석 상태 확인
  const checkAnalysisStatus = useCallback(() => {
    if (!caseId || !isTempCaseId(caseId)) return;

    const stored = localStorage.getItem(`analyzing_case_${caseId}`);
    if (!stored) return;

    try {
      const info: AnalyzingCaseInfo = JSON.parse(stored);
      setAnalyzingInfo(info);

      if (info.status === 'completed' && info.analysis) {
        // 폴링 중지
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }

        // 먼저 100% 진행률 표시
        setAnalysisProgress(100);

        // 잠시 후 결과 페이지로 이동 (사용자가 100% 완료를 볼 수 있도록)
        setTimeout(() => {
          setAnalysisStatus('completed');
          setCaseData(info.analysis!);
          setLoading(false);

          // 실제 case_id로 URL 업데이트
          // (localStorage 캐시는 loadCaseDetail에서 사용 후 삭제됨)
          if (info.realCaseId && info.realCaseId !== caseId) {
            navigate(`/cases-v2/${info.realCaseId}`, { replace: true });
          }
        }, 800); // 0.8초 후 이동
      } else if (info.status === 'failed') {
        // 분석 실패
        setAnalysisStatus('failed');
        setError(info.error || '분석 중 오류가 발생했습니다.');
        setLoading(false);

        // 폴링 중지
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      } else {
        // 아직 분석 중
        setAnalysisStatus('analyzing');

        // localStorage에 저장된 실제 진행 상태 사용
        if (info.progress !== undefined) {
          // 서버 응답 대기 중일 때는 시간 기반으로 30%에서 95%까지 천천히 증가
          if (info.stage === 'uploading' && info.progress >= 30) {
            const stageElapsed = Date.now() - (info.stageUpdatedAt || info.startTime || Date.now());
            const estimatedAnalysisTime = 45000; // 분석 예상 45초
            const analysisProgress = Math.min(
              95,
              30 + Math.round(65 * (1 - Math.exp(-stageElapsed / estimatedAnalysisTime * 2)))
            );
            setAnalysisProgress(analysisProgress);
            // 단계 라벨도 시간에 따라 업데이트
            if (analysisProgress < 40) {
              setStageLabel('문서 분석 중...');
              setCurrentStage('parsing');
            } else if (analysisProgress < 75) {
              setStageLabel('AI 분석 수행 중...');
              setCurrentStage('analyzing');
            } else {
              setStageLabel('결과 생성 중...');
              setCurrentStage('finalizing');
            }
          } else {
            setAnalysisProgress(info.progress);
            if (info.stageLabel) {
              setStageLabel(info.stageLabel);
            }
            if (info.stage) {
              setCurrentStage(info.stage);
            }
          }
        } else if (info.startTime) {
          // 진행 정보 없으면 시간 기반 추정 (fallback)
          const elapsed = Date.now() - info.startTime;
          const estimatedDuration = 30000;
          const ratio = elapsed / estimatedDuration;
          const progress = Math.min(95, Math.round(95 * (1 - Math.exp(-ratio * 2))));
          setAnalysisProgress(Math.max(progress, 5));
        }
      }
    } catch (e) {
      console.error('Error parsing analyzing info:', e);
    }
  }, [caseId, navigate]);

  // temp_ ID인 경우 폴링 시작
  useEffect(() => {
    if (isTempCaseId(caseId)) {
      setLoading(false); // temp_인 경우 API 로드 대기 불필요
      setAnalysisStatus('analyzing');

      // 초기 체크
      checkAnalysisStatus();

      // 폴링 시작 (1초 간격)
      pollingIntervalRef.current = setInterval(checkAnalysisStatus, 1000);

      // 클린업
      return () => {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      };
    }
  }, [caseId, checkAnalysisStatus]);

  // 일반 caseId인 경우 API 로드
  useEffect(() => {
    if (isValidCaseId(caseId) && !isTempCaseId(caseId)) {
      loadCaseDetail();
    }
  }, [caseId, token]);

  // 판례 검색 함수 (비동기)
  const searchPrecedents = useCallback(async () => {
    if (!isValidCaseId(caseId) || isTempCaseId(caseId) || precedentsSearched.current) return;

    precedentsSearched.current = true;
    setPrecedentsLoading(true);
    setPrecedentsStatus('searching');

    try {
      console.log('[CaseDetailV2] Starting precedent search for case:', caseId);
      const response = await apiClient.searchPrecedentsForCase(caseId, token || undefined);

      if (response.success && response.precedents) {
        // caseData 업데이트
        setCaseData(prev => prev ? {
          ...prev,
          related_precedents: response.precedents
        } : prev);
        setPrecedentsStatus('completed');
        console.log('[CaseDetailV2] Precedent search completed:', response.precedents.length);
      } else {
        setPrecedentsStatus('failed');
        console.error('[CaseDetailV2] Precedent search failed:', response.error);
      }
    } catch (err) {
      console.error('[CaseDetailV2] Precedent search error:', err);
      setPrecedentsStatus('failed');
    } finally {
      setPrecedentsLoading(false);
    }
  }, [caseId, token]);

  const loadCaseDetail = async () => {
    if (!isValidCaseId(caseId) || isTempCaseId(caseId)) return;

    // 1. 먼저 localStorage에서 방금 완료된 분석 캐시 확인
    // (navigate 후 불필요한 API 재호출 방지)
    const cacheKeys = Object.keys(localStorage).filter(k => k.startsWith('analyzing_case_temp_'));
    for (const key of cacheKeys) {
      try {
        const cached: AnalyzingCaseInfo = JSON.parse(localStorage.getItem(key) || '{}');
        if (cached.realCaseId === caseId && cached.analysis && cached.status === 'completed') {
          console.log('[CaseDetailV2] Using cached analysis data, skipping API call');
          setCaseData(cached.analysis);
          setAnalysisStatus('completed');
          setLoading(false);

          // 캐시 정리
          localStorage.removeItem(key);

          // 판례 상태 설정
          if (!cached.analysis.related_precedents || cached.analysis.related_precedents.length === 0) {
            setPrecedentsStatus('pending');
          } else {
            setPrecedentsStatus('completed');
          }
          return; // API 호출 스킵
        }
      } catch (e) {
        // 파싱 오류 무시
      }
    }

    // 2. 캐시가 없으면 API 호출
    setLoading(true);
    setError(null);

    try {
      const analysis: CriminalCaseAnalysis = await apiClient.getCriminalCase(caseId, token || undefined);
      setCaseData(analysis);
      setAnalysisStatus('completed');

      // 판례가 없으면 비동기로 검색 시작
      if (!analysis.related_precedents || analysis.related_precedents.length === 0) {
        setPrecedentsStatus('pending');
      } else {
        setPrecedentsStatus('completed');
      }
    } catch (err) {
      console.error('Error loading case details:', err);
      // 폴백 (기존 백엔드 API - 인증 불필요)
      try {
        const fallbackAnalysis = await apiClient.getCase(caseId);
        setCaseData(fallbackAnalysis as CriminalCaseAnalysis);
        setAnalysisStatus('completed');
      } catch (fallbackErr) {
        console.error('Fallback also failed:', fallbackErr);
        setError('사건 정보를 불러오는데 실패했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  // 판례가 없고 상세 페이지 로드 완료 시 자동으로 검색 시작
  useEffect(() => {
    if (
      caseData &&
      analysisStatus === 'completed' &&
      precedentsStatus === 'pending' &&
      !precedentsLoading &&
      !precedentsSearched.current
    ) {
      searchPrecedents();
    }
  }, [caseData, analysisStatus, precedentsStatus, precedentsLoading, searchPrecedents]);

  // 사건 삭제
  const handleDeleteCase = async () => {
    if (!caseId || !window.confirm('정말로 이 사건을 삭제하시겠습니까?')) return;

    try {
      await apiClient.deleteCriminalCase(caseId, token || undefined);
      navigate('/cases-v2');
    } catch (err) {
      // 폴백
      try {
        await apiClient.deleteCase(caseId, token || undefined);
        navigate('/cases-v2');
      } catch (fallbackErr) {
        console.error('Error deleting case:', fallbackErr);
        alert('사건 삭제 중 오류가 발생했습니다.');
      }
    }
  };

  // 목록으로 돌아가기
  const handleBack = () => {
    navigate('/cases-v2');
  };

  // 분석 중인지 확인 (temp_ ID이고 아직 완료되지 않은 경우)
  const isAnalyzing = useMemo(() => {
    return analysisStatus === 'analyzing';
  }, [analysisStatus]);

  // 분석 실패인지 확인
  const isFailed = useMemo(() => {
    return analysisStatus === 'failed';
  }, [analysisStatus]);

  // PII 부분 마스킹 적용된 데이터 (summary 탭에서만 사용)
  const maskedSummaryData = useMemo(() => {
    if (!caseData) return null;
    return {
      // summary 탭에 필요한 필드만 마스킹
      summary: applyPartialMasking(caseData.summary || ''),
      parties: caseData.parties
        ? Object.fromEntries(
            Object.entries(caseData.parties).map(([role, name]) => [
              role,
              typeof name === 'string' ? maskKoreanName(name) : name,
            ])
          )
        : undefined,
      issues: caseData.issues?.map((issue) => applyPartialMasking(issue)),
      scenario: caseData.scenario
        ? {
            ...caseData.scenario,
            scenario_name: applyPartialMasking(caseData.scenario.scenario_name || ''),
            description: applyPartialMasking(caseData.scenario.description || ''),
          }
        : undefined,
    };
  }, [caseData]);

  if (loading) {
    return (
      <div className="case-detail-v2">
        <div className="detail-loading">
          <FiLoader className="spin" />
          <p>사건 정보를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  // 분석 중일 때는 에러 화면 대신 분석 진행 UI를 보여줌
  if ((error || !caseData) && !isAnalyzing) {
    return (
      <div className="case-detail-v2">
        <div className={`detail-error ${isFailed ? 'failed' : ''}`}>
          <FiAlertCircle />
          <p>{error || '사건 정보를 찾을 수 없습니다.'}</p>
          <button className="btn-primary" onClick={handleBack}>
            <FiArrowLeft /> 목록으로 돌아가기
          </button>
          {isFailed && (
            <button
              className="btn-secondary"
              onClick={() => {
                // localStorage 정리 후 다시 시도
                if (caseId) {
                  localStorage.removeItem(`analyzing_case_${caseId}`);
                }
                navigate('/case');
              }}
              style={{ marginLeft: '12px' }}
            >
              다시 분석하기
            </button>
          )}
        </div>
      </div>
    );
  }

  // 분석 중 화면
  if (isAnalyzing) {
    return (
      <div className="case-detail-v2">
        <header className="detail-header">
          <div className="header-left">
            <button className="btn-back" onClick={handleBack}>
              <FiArrowLeft />
              <span>목록</span>
            </button>
            <div className="case-title-area">
              <h1>{analyzingInfo?.tempCase?.case_name || '문서 분석 중'}</h1>
              <div className="case-meta">
                {analyzingInfo?.documentCategory && (
                  <span className="crime-type-badge">{analyzingInfo.documentCategory}</span>
                )}
                {analyzingInfo?.files && (
                  <span className="meta-info">{analyzingInfo.files.length}개 문서</span>
                )}
              </div>
            </div>
          </div>
        </header>

        <div className="analyzing-container">
          <div className="analyzing-status">
            <div className="analyzing-animation">
              <div className="analyzing-spinner">
                <FiCpu className="analyzing-icon" />
              </div>
              <div className="analyzing-progress">
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${analysisProgress}%` }}
                  ></div>
                </div>
                <span className="progress-text">{analysisProgress}%</span>
              </div>
            </div>
            <h2>AI가 문서를 분석하고 있습니다</h2>
            <p className="analyzing-description">
              {stageLabel}
            </p>
            <div className="analyzing-steps">
              <div className={`step ${currentStage === 'uploading' ? 'active' : ''} ${['parsing', 'analyzing', 'finalizing', 'completed'].includes(currentStage) ? 'completed' : ''}`}>
                {['parsing', 'analyzing', 'finalizing', 'completed'].includes(currentStage) ? <FiCheckCircle /> : <FiFileText />}
                <span>파일 업로드</span>
              </div>
              <div className={`step ${currentStage === 'parsing' ? 'active' : ''} ${['analyzing', 'finalizing', 'completed'].includes(currentStage) ? 'completed' : ''}`}>
                {['analyzing', 'finalizing', 'completed'].includes(currentStage) ? <FiCheckCircle /> : <FiFileText />}
                <span>문서 파싱</span>
              </div>
              <div className={`step ${currentStage === 'analyzing' || currentStage === 'searching' ? 'active' : ''} ${['finalizing', 'completed'].includes(currentStage) ? 'completed' : ''}`}>
                {['finalizing', 'completed'].includes(currentStage) ? <FiCheckCircle /> : <FiCpu />}
                <span>AI 분석</span>
              </div>
              <div className={`step ${currentStage === 'finalizing' || currentStage === 'completed' ? 'active' : ''}`}>
                {currentStage === 'completed' ? <FiCheckCircle /> : <FiShield />}
                <span>결과 생성</span>
              </div>
            </div>
            {analyzingInfo?.startTime && (
              <p className="analyzing-time">
                경과 시간: {Math.round((Date.now() - analyzingInfo.startTime) / 1000)}초
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // TypeScript를 위한 null 체크 (위 로직상 여기 도달 시 caseData는 항상 존재)
  if (!caseData) {
    return null;
  }

  return (
    <div className="case-detail-v2">
      {/* 상단 헤더 */}
      <header className="detail-header">
        <div className="header-left">
          <button className="btn-back" onClick={handleBack}>
            <FiArrowLeft />
            <span>목록</span>
          </button>
          <div className="case-title-area">
            <h1>{caseData?.suggested_case_name || caseData?.case_name}</h1>
            <div className="case-meta">
              {caseData?.crime_type && (
                <span className="crime-type-badge">{caseData.crime_type}</span>
              )}
              {caseData?.uploaded_files && (
                <span className="meta-info">{caseData.uploaded_files.length}개 문서</span>
              )}
            </div>
          </div>
        </div>
        <div className="header-right">
          {/* 뷰 모드 토글 */}
          <div className="view-mode-toggle">
            <button
              className={viewMode === 'simple' ? 'active' : ''}
              onClick={() => setViewMode('simple')}
              title="쉬운 용어로 분석 결과를 확인합니다"
            >
              <FiUser /> 쉬운 설명
            </button>
            <button
              className={viewMode === 'expert' ? 'active' : ''}
              onClick={() => setViewMode('expert')}
              title="법률 전문 용어로 상세 분석을 확인합니다"
            >
              <FiBriefcase /> 전문가 분석
            </button>
          </div>
          {caseData?.uploaded_files && caseData.uploaded_files.length > 0 && (
            <button
              className="btn-view-document"
              onClick={() => setShowDocumentPanel(true)}
            >
              <FiFileText /> 원문 보기
            </button>
          )}
          <button
            className="btn-danger"
            onClick={handleDeleteCase}
          >
            <FiTrash2 /> 삭제
          </button>
        </div>
      </header>

      {/* 분석 완료 - 탭 기반 UI */}
      <div className="detail-content">
          {/* 탭 네비게이션 */}
          <nav className="detail-tabs">
            <button
              className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`}
              onClick={() => setActiveTab('summary')}
            >
              <FiList /> {viewMode === 'simple' ? '요약' : '사건 요약'}
            </button>
            <button
              className={`tab-btn ${activeTab === 'elements' ? 'active' : ''}`}
              onClick={() => setActiveTab('elements')}
            >
              <FiTarget /> {viewMode === 'simple' ? '가능성' : '구성요건'}
            </button>
            <button
              className={`tab-btn ${activeTab === 'sentencing' ? 'active' : ''}`}
              onClick={() => setActiveTab('sentencing')}
            >
              <FiSliders /> {viewMode === 'simple' ? '예상 결과' : '양형'}
            </button>
            <button
              className={`tab-btn ${activeTab === 'precedents' ? 'active' : ''}`}
              onClick={() => setActiveTab('precedents')}
            >
              <FiBook /> 관련 판례
            </button>
            <button
              className={`tab-btn ${activeTab === 'nextsteps' ? 'active' : ''}`}
              onClick={() => setActiveTab('nextsteps')}
            >
              <FiArrowRight /> 다음 단계
            </button>
          </nav>

          {/* 탭 콘텐츠 */}
          <div className="tab-content">
            {/* 요약 탭 (PII 부분 마스킹 적용) */}
            {activeTab === 'summary' && (
              <div className="tab-panel">
                <div className="detail-section">
                  <h3>{viewMode === 'simple' ? '무슨 일이 있었나요?' : '사건 요약'}</h3>
                  <p className="summary-text">{maskedSummaryData?.summary}</p>
                </div>

                {/* 당사자 정보 (PII 마스킹 적용) */}
                {maskedSummaryData?.parties && Object.keys(maskedSummaryData.parties).length > 0 && (
                  <div className="detail-section">
                    <h3>{viewMode === 'simple' ? '관련된 사람들' : '당사자'}</h3>
                    <ul className="parties-list">
                      {Object.entries(maskedSummaryData.parties).map(([role, name]) => (
                        <li key={role}>
                          <strong>{role}:</strong> {name}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 주요 쟁점 (PII 마스킹 적용) */}
                {maskedSummaryData?.issues && maskedSummaryData.issues.length > 0 && (
                  <div className="detail-section">
                    <h3>{viewMode === 'simple' ? '핵심 문제' : '주요 쟁점'}</h3>
                    <ul className="issues-list">
                      {maskedSummaryData.issues.map((issue, idx) => (
                        <li key={idx}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 주요 날짜 (마스킹 불필요) */}
                {caseData?.key_dates && Object.keys(caseData.key_dates).length > 0 && (
                  <div className="detail-section">
                    <h3>{viewMode === 'simple' ? '중요한 날짜' : '주요 날짜'}</h3>
                    <ul className="dates-list">
                      {Object.entries(caseData.key_dates).map(([label, date]) => (
                        <li key={label}>
                          <strong>{label}:</strong> {date}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 시나리오 (AI 분석, PII 마스킹 적용) */}
                {maskedSummaryData?.scenario && (
                  <div className="detail-section scenario-section">
                    <h3>{viewMode === 'simple' ? 'AI가 판단한 사건 유형' : 'AI 분석 - 사건 유형'}</h3>
                    <div className="scenario-info-card">
                      <div className="scenario-name">
                        <FiCpu />
                        <span>{maskedSummaryData.scenario.scenario_name}</span>
                        <span className="confidence">
                          {Math.round((caseData?.scenario?.confidence || 0) * 100)}% 확신
                        </span>
                      </div>
                      <p className="scenario-desc">{maskedSummaryData.scenario.description}</p>
                      <button
                        className="btn-primary"
                        onClick={() => navigate(`/docs?caseId=${caseData?.case_id}`)}
                      >
                        <FiEdit /> 문서 생성하기
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 구성요건/가능성 탭 (마스킹 미적용) */}
            {activeTab === 'elements' && (
              <div className="tab-panel">
                {viewMode === 'simple' ? (
                  <>
                    {caseData?.crime_elements ? (
                      <PossibilityCard analysis={caseData} />
                    ) : (
                      <div className="empty-tab-state">
                        <FiTarget />
                        <p>아직 구성요건 분석 결과가 없습니다.</p>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    {caseData?.crime_elements ? (
                      <CrimeElementsCard elements={caseData.crime_elements} />
                    ) : (
                      <div className="empty-tab-state">
                        <FiTarget />
                        <p>아직 구성요건 분석 결과가 없습니다.</p>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* 양형/예상 결과 탭 (마스킹 미적용) */}
            {activeTab === 'sentencing' && (
              <div className="tab-panel">
                {viewMode === 'simple' ? (
                  <>
                    {caseData?.sentencing_factors && (
                      <SimpleFactorsCard
                        factors={caseData.sentencing_factors}
                        role="victim"
                      />
                    )}
                    {caseData?.expected_sentence && (
                      <ExpectedResultCard
                        sentence={caseData.expected_sentence}
                        crimeType={caseData.crime_type || ''}
                        role="victim"
                      />
                    )}
                    {!caseData?.sentencing_factors && !caseData?.expected_sentence && (
                      <div className="empty-tab-state">
                        <FiSliders />
                        <p>아직 양형 분석 결과가 없습니다.</p>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    {caseData?.sentencing_factors && (
                      <SentencingFactorsCard factors={caseData.sentencing_factors} />
                    )}
                    {caseData?.expected_sentence && (
                      <SentenceEstimateCard sentence={caseData.expected_sentence} />
                    )}
                    {caseData?.defense_strategies && caseData.defense_strategies.length > 0 && (
                      <DefenseStrategiesCard strategies={caseData.defense_strategies} />
                    )}
                    {!caseData?.sentencing_factors && !caseData?.expected_sentence && (
                      <div className="empty-tab-state">
                        <FiSliders />
                        <p>아직 양형 분석 결과가 없습니다.</p>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* 관련 판례 탭 (마스킹 미적용) */}
            {activeTab === 'precedents' && (
              <div className="tab-panel">
                {/* 판례 검색 중 상태 */}
                {precedentsLoading || precedentsStatus === 'searching' ? (
                  <div className="precedents-loading-state">
                    <div className="loading-spinner">
                      <FiLoader className="spin" />
                    </div>
                    <h3>관련 판례를 검색하고 있습니다</h3>
                    <p>유사한 사건의 판례를 AI가 분석하고 있습니다...</p>
                    <div className="loading-bar">
                      <div className="loading-bar-fill"></div>
                    </div>
                  </div>
                ) : precedentsStatus === 'failed' ? (
                  <div className="precedents-error-state">
                    <FiAlertCircle />
                    <h3>판례 검색 실패</h3>
                    <p>관련 판례를 검색하는 중 오류가 발생했습니다.</p>
                    <button
                      className="btn-retry"
                      onClick={() => {
                        precedentsSearched.current = false;
                        searchPrecedents();
                      }}
                    >
                      다시 시도
                    </button>
                  </div>
                ) : caseData?.related_precedents && caseData.related_precedents.length > 0 ? (
                  <CriminalPrecedentCard precedents={caseData.related_precedents} />
                ) : caseData?.related_cases && caseData.related_cases.length > 0 ? (
                  <div className="detail-section">
                    <h3>{viewMode === 'simple' ? '비슷한 사례들' : '관련 판례'}</h3>
                    <ul className="related-cases">
                      {caseData.related_cases.map((relatedCase, idx) => (
                        <li key={idx}>
                          <strong>{relatedCase.title}</strong>
                          <p>{relatedCase.summary}</p>
                          <span className="relevance">관련도: {relatedCase.relevance}%</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <div className="empty-tab-state">
                    <FiBook />
                    <p>{viewMode === 'simple' ? '아직 비슷한 사례를 찾지 못했습니다.' : '관련 판례가 없습니다.'}</p>
                  </div>
                )}
              </div>
            )}

            {/* 다음 단계 탭 (마스킹 미적용) */}
            {activeTab === 'nextsteps' && (
              <div className="tab-panel">
                {viewMode === 'simple' ? (
                  <NextStepsCard analysis={caseData} />
                ) : (
                  <>
                    {caseData?.suggested_next_steps && caseData.suggested_next_steps.length > 0 ? (
                      <div className="detail-section">
                        <h3>다음 단계 제안</h3>
                        <ul className="next-steps-list">
                          {caseData.suggested_next_steps.map((step, idx) => (
                            <li key={idx}>
                              <span className="step-number">{idx + 1}</span>
                              <span>{step}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <div className="empty-tab-state">
                        <FiArrowRight />
                        <p>다음 단계 제안이 없습니다.</p>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>

      {/* 원문 보기 슬라이드 패널 (마스킹 미적용 - 원본 표시) */}
      {showDocumentPanel && caseData && (
        <div className="document-panel-overlay" onClick={() => setShowDocumentPanel(false)}>
          <aside className="document-slide-panel" onClick={(e) => e.stopPropagation()}>
            <div className="panel-header">
              <h2>원본 문서</h2>
              <button className="btn-close-panel" onClick={() => setShowDocumentPanel(false)}>
                <FiX />
              </button>
            </div>
            <div className="panel-body">
              {caseData?.uploaded_files && caseData.uploaded_files.length > 0 ? (
                <div className="document-list-panel">
                  {caseData.uploaded_files.map((file, idx) => (
                    <div key={idx} className="document-item-panel">
                      <div className="document-item-header">
                        <FiFileText />
                        <span className="filename">{file.filename}</span>
                        <span className="filesize">({(file.size / 1024).toFixed(1)} KB)</span>
                      </div>
                      {file.content && (
                        <div className="document-content-preview">
                          <pre>{file.content}</pre>
                        </div>
                      )}
                      {!file.content && (
                        <div className="no-content-message">
                          <p>{viewMode === 'simple' ? '미리보기를 지원하지 않는 파일입니다.' : '원문 미리보기를 사용할 수 없습니다.'}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-panel-state">
                  <FiFileText />
                  <p>업로드된 문서가 없습니다.</p>
                </div>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
};

export default CaseDetailV2;
