import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiShield, FiPlus, FiRefreshCw, FiLoader } from 'react-icons/fi';
import apiClient from '../../api/client';
import { useAuth } from '../../contexts/AuthContext';
import {
  CriminalCase,
  CriminalDashboardSummary,
  CriminalRecommendation
} from '../../types';

// 컴포넌트 임포트
import ProgressTimeline from './components/ProgressTimeline';
import CaseOverviewCard from './components/CaseOverviewCard';
import UpcomingSchedule from './components/UpcomingSchedule';
import StageDistributionChart from './components/StageDistributionChart';
import CrimeTypeChart from './components/CrimeTypeChart';

import './CriminalDashboard.css';

const CriminalDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { token } = useAuth();

  // 상태
  const [cases, setCases] = useState<CriminalCase[]>([]);
  const [dashboardSummary, setDashboardSummary] = useState<CriminalDashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // 권장 사항 생성 (모든 사건의 일정 기반)
  const recommendations = useMemo((): CriminalRecommendation[] => {
    if (cases.length === 0) return [];

    const recs: CriminalRecommendation[] = [];

    // 모든 사건의 다가오는 일정 확인
    const allUpcomingSchedules = cases
      .flatMap(c => (c.schedules || []).map(s => ({ ...s, caseName: c.case_name })))
      .filter(s => !s.is_completed)
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    if (allUpcomingSchedules.length > 0) {
      const nextSchedule = allUpcomingSchedules[0];
      const daysUntil = Math.ceil(
        (new Date(nextSchedule.date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
      );

      if (daysUntil <= 7) {
        recs.push({
          priority: daysUntil <= 3 ? 'HIGH' : 'MEDIUM',
          content: `${nextSchedule.title} 준비 (${daysUntil}일 후)`,
        });
      }
    }

    // 진행 중인 사건별 권장 사항
    const activeCases = cases.filter(c => c.stage !== 'CLOSED');
    activeCases.slice(0, 2).forEach(c => {
      switch (c.stage) {
        case 'INVESTIGATION':
          recs.push({ priority: 'MEDIUM', content: `[${c.case_name}] 피해자 합의 검토` });
          break;
        case 'PROSECUTION':
          recs.push({ priority: 'HIGH', content: `[${c.case_name}] 변호인 선임 확인` });
          break;
        case 'TRIAL':
          recs.push({ priority: 'HIGH', content: `[${c.case_name}] 공판 준비` });
          break;
      }
    });

    return recs.slice(0, 4);
  }, [cases]);

  // 데이터 로드
  const loadData = async (showRefreshing = false) => {
    if (showRefreshing) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      // 형사 사건 목록 로드
      const casesResponse = await apiClient.getCriminalCasesForDashboard(token || undefined);
      setCases(casesResponse.cases || []);

      // 대시보드 요약 로드 (선택적)
      try {
        const summary = await apiClient.getCriminalDashboardSummary(token || undefined);
        setDashboardSummary(summary);
      } catch {
        // 요약 API가 없어도 기본 기능은 동작
        console.log('Dashboard summary API not available');
      }
    } catch (err: any) {
      // 폴백: 일반 케이스 API에서 데이터 변환
      try {
        const fallbackResponse = await apiClient.getCriminalCases(token || undefined);
        // CriminalCaseListItem을 CriminalCase로 변환
        const convertedCases: CriminalCase[] = (fallbackResponse.cases || []).map(item => ({
          id: item.case_id,
          user_id: '',
          case_name: item.case_name,
          summary: item.summary,
          crime_type: item.crime_type || '',
          crime_elements: { objective: [], subjective: [] },
          sentencing_factors: { favorable: [], unfavorable: [] },
          expected_sentence: { range: '', suspended_probability: 0 },
          defense_strategies: [],
          related_precedents: [],
          stage: item.stage || 'INVESTIGATION',
          schedules: item.next_schedule ? [item.next_schedule] : [],
          conditions: [],
          uploaded_files: [],
          created_at: new Date(item.created_at * 1000).toISOString(),
          updated_at: new Date(item.created_at * 1000).toISOString(),
        }));
        setCases(convertedCases);
      } catch (fallbackErr) {
        setError('사건 데이터를 불러오는데 실패했습니다.');
        console.error('Failed to load cases:', fallbackErr);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadData();
    }
  }, [token]);

  // 새로고침 핸들러
  const handleRefresh = () => {
    loadData(true);
  };

  // 새 사건 등록 핸들러
  const handleNewCase = () => {
    navigate('/cases-v2');
  };

  // 사건 상세 보기 핸들러
  const handleViewCase = (caseId: string) => {
    navigate(`/cases-v2?caseId=${caseId}`);
  };

  // 로딩 상태
  if (loading) {
    return (
      <div className="criminal-dashboard loading-state">
        <div className="loading-container">
          <FiLoader className="spinner" />
          <p>형사사건 현황을 불러오는 중...</p>
        </div>
      </div>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <div className="criminal-dashboard error-state">
        <div className="error-container">
          <FiShield className="error-icon" />
          <p>{error}</p>
          <button className="btn-secondary" onClick={() => loadData()}>
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="criminal-dashboard">
      {/* 헤더 */}
      <div className="dashboard-header">
        <div className="header-title">
          <FiShield className="header-icon" />
          <h1>형사사건 현황</h1>
        </div>
        <div className="header-actions">
          <button
            className="btn-secondary"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <FiRefreshCw className={refreshing ? 'spinning' : ''} />
            {refreshing ? '새로고침 중...' : '새로고침'}
          </button>
          <button className="btn-primary" onClick={handleNewCase}>
            <FiPlus /> 새 사건 등록
          </button>
        </div>
      </div>

      {/* 사건이 없는 경우 */}
      {cases.length === 0 ? (
        <div className="empty-dashboard">
          <FiShield className="empty-icon" />
          <h2>등록된 형사 사건이 없습니다</h2>
          <p>새 사건을 등록하여 AI 기반 형사법 분석을 시작하세요.</p>
          <button className="btn-primary" onClick={handleNewCase}>
            <FiPlus /> 첫 사건 등록하기
          </button>
        </div>
      ) : (
        <>
          {/* 진행 상황 타임라인 */}
          <ProgressTimeline cases={cases} />

          {/* 상단 그리드: 현황 + 일정 */}
          <div className="dashboard-top-grid">
            <CaseOverviewCard cases={cases} />
            <UpcomingSchedule cases={cases} recommendations={recommendations} />
          </div>

          {/* 하단 그리드: 차트 2개 */}
          <div className="dashboard-charts-grid">
            <StageDistributionChart cases={cases} />
            <CrimeTypeChart cases={cases} />
          </div>
        </>
      )}
    </div>
  );
};

export default CriminalDashboard;
