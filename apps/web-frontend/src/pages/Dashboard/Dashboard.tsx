/**
 * LawLawKR Dashboard Hub
 * 통합 대시보드 - 서비스 전반 현황을 한눈에
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FiFolder,
  FiAlertTriangle,
  FiFileText,
  FiCheckCircle,
  FiClock,
  FiChevronRight,
  FiRefreshCw,
  FiActivity,
  FiCalendar,
  FiShield,
  FiMessageSquare,
  FiTrendingUp,
  FiLoader,
} from 'react-icons/fi';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import apiClient from '../../api/client';
import { useAuth } from '../../contexts/AuthContext';
import {
  CriminalCase,
  RiskOverview,
  CriminalScheduleItem,
  RiskDocumentListItem,
} from '../../types';
import './Dashboard.css';

// Stage colors for criminal cases
const STAGE_COLORS: Record<string, string> = {
  COMPLAINT: '#94a3b8',
  INVESTIGATION: '#f59e0b',
  PROSECUTION: '#3b82f6',
  TRIAL: '#8b5cf6',
  JUDGMENT: '#10b981',
  CLOSED: '#6b7280',
};

const STAGE_LABELS: Record<string, string> = {
  COMPLAINT: '고소/고발',
  INVESTIGATION: '수사',
  PROSECUTION: '기소',
  TRIAL: '재판',
  JUDGMENT: '판결',
  CLOSED: '종결',
};

// Risk severity colors
const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#dc2626',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#22c55e',
  INFO: '#3b82f6',
};

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { token } = useAuth();

  // States
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [cases, setCases] = useState<CriminalCase[]>([]);
  const [riskOverview, setRiskOverview] = useState<RiskOverview | null>(null);
  const [recentDocuments, setRecentDocuments] = useState<RiskDocumentListItem[]>([]);

  // Load all dashboard data
  const loadData = useCallback(async (showRefreshing = false) => {
    if (!token) return;

    if (showRefreshing) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      // Load criminal cases
      const casesResponse = await apiClient.getCriminalCasesForDashboard(token);
      setCases(casesResponse.cases || []);

      // Load risk overview
      try {
        const riskData = await apiClient.getRiskOverview(token);
        setRiskOverview(riskData);
      } catch {
        console.log('Risk overview API not available');
      }

      // Load recent risk documents
      try {
        const docsData = await apiClient.getDocumentsWithRisk({
          page: 1,
          page_size: 3,
          sort_by: 'created_at',
          sort_order: 'desc',
        }, token);
        setRecentDocuments(docsData.results || []);
      } catch {
        console.log('Risk documents API not available');
      }
    } catch (err: any) {
      setError('데이터를 불러오는데 실패했습니다.');
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Computed stats
  const stats = {
    totalCases: cases.length,
    activeCases: cases.filter(c => c.stage !== 'CLOSED').length,
    highRiskDocs: riskOverview?.high_risk_count || 0,
    analyzedDocs: riskOverview?.documents_with_risk || 0,
  };

  // Get upcoming schedules from all cases
  const upcomingSchedules = cases
    .flatMap(c => (c.schedules || []).map(s => ({
      ...s,
      caseName: c.case_name,
      caseId: c.id,
    })))
    .filter(s => !s.is_completed && new Date(s.date) >= new Date())
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    .slice(0, 5);

  // Get stage distribution for mini chart
  const stageDistribution = Object.entries(
    cases.reduce((acc, c) => {
      acc[c.stage] = (acc[c.stage] || 0) + 1;
      return acc;
    }, {} as Record<string, number>)
  ).map(([stage, count]) => ({
    name: stage,
    value: count,
    color: STAGE_COLORS[stage] || '#6b7280',
  }));

  // Get severity distribution for mini chart
  const severityDistribution = riskOverview
    ? Object.entries(riskOverview.severity_distribution || {})
        .filter(([_, value]) => value > 0)
        .map(([key, value]) => ({
          name: key,
          value,
          color: SEVERITY_COLORS[key] || '#6b7280',
        }))
    : [];

  // Recent activities (mock for now, can be replaced with real API)
  const recentActivities = [
    ...cases.slice(0, 2).map(c => ({
      type: 'case',
      title: c.case_name,
      subtitle: `${STAGE_LABELS[c.stage] || c.stage} 단계`,
      time: c.created_at,
      icon: <FiFolder />,
    })),
    ...recentDocuments.slice(0, 2).map(d => ({
      type: 'document',
      title: d.document.title,
      subtitle: `리스크 분석 완료`,
      time: d.document.created_at,
      icon: <FiFileText />,
    })),
  ].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
   .slice(0, 4);

  // Format date helper
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return '오늘';
    if (diffDays === 1) return '내일';
    if (diffDays > 0 && diffDays <= 7) return `${diffDays}일 후`;

    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  };

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 60) return `${diffMins}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    if (diffDays < 7) return `${diffDays}일 전`;
    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <div className="dashboard-hub loading-state">
        <div className="loading-container">
          <FiLoader className="spinner" />
          <p>대시보드를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-hub error-state">
        <div className="error-container">
          <FiAlertTriangle className="error-icon" />
          <p>{error}</p>
          <button className="btn-primary" onClick={() => loadData()}>
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-hub">
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-left">
          <h1>대시보드</h1>
          <p className="header-subtitle">서비스 현황을 한눈에 확인하세요</p>
        </div>
        <div className="header-actions">
          <button
            className="btn-secondary"
            onClick={() => loadData(true)}
            disabled={refreshing}
          >
            <FiRefreshCw className={refreshing ? 'spinning' : ''} />
            {refreshing ? '새로고침 중...' : '새로고침'}
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="quick-stats">
        <div className="stat-card" onClick={() => navigate('/criminal-dashboard')}>
          <div className="stat-icon cases">
            <FiFolder />
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats.totalCases}</span>
            <span className="stat-label">전체 사건</span>
          </div>
          <FiChevronRight className="stat-arrow" />
        </div>

        <div className="stat-card" onClick={() => navigate('/criminal-dashboard')}>
          <div className="stat-icon active">
            <FiActivity />
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats.activeCases}</span>
            <span className="stat-label">진행중 사건</span>
          </div>
          <FiChevronRight className="stat-arrow" />
        </div>

        <div className="stat-card warning" onClick={() => navigate('/risk-dashboard')}>
          <div className="stat-icon risk">
            <FiAlertTriangle />
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats.highRiskDocs}</span>
            <span className="stat-label">고위험 문서</span>
          </div>
          <FiChevronRight className="stat-arrow" />
        </div>

        <div className="stat-card" onClick={() => navigate('/documents')}>
          <div className="stat-icon docs">
            <FiCheckCircle />
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats.analyzedDocs}</span>
            <span className="stat-label">분석 완료</span>
          </div>
          <FiChevronRight className="stat-arrow" />
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="dashboard-grid">
        {/* Cases Summary Card */}
        <div className="summary-card cases-summary">
          <div className="card-header">
            <div className="card-title">
              <FiShield className="card-icon" />
              <h3>사건 현황</h3>
            </div>
            <button className="link-btn" onClick={() => navigate('/criminal-dashboard')}>
              상세보기 <FiChevronRight />
            </button>
          </div>

          <div className="card-content">
            {cases.length === 0 ? (
              <div className="empty-state">
                <FiFolder className="empty-icon" />
                <p>등록된 사건이 없습니다</p>
                <button className="btn-primary small" onClick={() => navigate('/cases-v2')}>
                  사건 등록하기
                </button>
              </div>
            ) : (
              <>
                <div className="mini-chart-section">
                  {stageDistribution.length > 0 && (
                    <div className="mini-chart">
                      <ResponsiveContainer width={100} height={100}>
                        <PieChart>
                          <Pie
                            data={stageDistribution}
                            dataKey="value"
                            cx="50%"
                            cy="50%"
                            innerRadius={30}
                            outerRadius={45}
                          >
                            {stageDistribution.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="chart-center">
                        <span className="center-value">{cases.length}</span>
                        <span className="center-label">건</span>
                      </div>
                    </div>
                  )}
                  <div className="stage-legend">
                    {stageDistribution.map(item => (
                      <div key={item.name} className="legend-item">
                        <span
                          className="legend-dot"
                          style={{ backgroundColor: item.color }}
                        />
                        <span className="legend-text">
                          {STAGE_LABELS[item.name] || item.name}
                        </span>
                        <span className="legend-count">{item.value}건</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="recent-list">
                  <h4>최근 사건</h4>
                  {cases.slice(0, 3).map(c => (
                    <div
                      key={c.id}
                      className="recent-item"
                      onClick={() => navigate(`/cases-v2?caseId=${c.id}`)}
                    >
                      <div className="item-info">
                        <span className="item-title">{c.case_name}</span>
                        <span
                          className="stage-badge"
                          style={{ backgroundColor: STAGE_COLORS[c.stage] }}
                        >
                          {STAGE_LABELS[c.stage] || c.stage}
                        </span>
                      </div>
                      <FiChevronRight className="item-arrow" />
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Risk Summary Card */}
        <div className="summary-card risk-summary">
          <div className="card-header">
            <div className="card-title">
              <FiAlertTriangle className="card-icon" />
              <h3>리스크 현황</h3>
            </div>
            <button className="link-btn" onClick={() => navigate('/risk-dashboard')}>
              상세보기 <FiChevronRight />
            </button>
          </div>

          <div className="card-content">
            {!riskOverview || riskOverview.documents_with_risk === 0 ? (
              <div className="empty-state">
                <FiFileText className="empty-icon" />
                <p>분석된 문서가 없습니다</p>
                <button className="btn-primary small" onClick={() => navigate('/documents')}>
                  문서 업로드
                </button>
              </div>
            ) : (
              <>
                <div className="mini-chart-section">
                  {severityDistribution.length > 0 && (
                    <div className="mini-chart">
                      <ResponsiveContainer width={100} height={100}>
                        <PieChart>
                          <Pie
                            data={severityDistribution}
                            dataKey="value"
                            cx="50%"
                            cy="50%"
                            innerRadius={30}
                            outerRadius={45}
                          >
                            {severityDistribution.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="chart-center">
                        <span className="center-value">
                          {riskOverview?.avg_risk_score?.toFixed(0) || 0}
                        </span>
                        <span className="center-label">점</span>
                      </div>
                    </div>
                  )}
                  <div className="risk-stats">
                    <div className="risk-stat critical">
                      <span className="risk-count">
                        {riskOverview?.severity_distribution?.CRITICAL || 0}
                      </span>
                      <span className="risk-label">심각</span>
                    </div>
                    <div className="risk-stat high">
                      <span className="risk-count">
                        {riskOverview?.severity_distribution?.HIGH || 0}
                      </span>
                      <span className="risk-label">높음</span>
                    </div>
                    <div className="risk-stat medium">
                      <span className="risk-count">
                        {riskOverview?.severity_distribution?.MEDIUM || 0}
                      </span>
                      <span className="risk-label">중간</span>
                    </div>
                    <div className="risk-stat low">
                      <span className="risk-count">
                        {riskOverview?.severity_distribution?.LOW || 0}
                      </span>
                      <span className="risk-label">낮음</span>
                    </div>
                  </div>
                </div>

                <div className="recent-list">
                  <h4>최근 분석 문서</h4>
                  {recentDocuments.map(doc => (
                    <div
                      key={doc.document.id}
                      className="recent-item"
                      onClick={() => navigate(`/documents/${doc.document.id}`)}
                    >
                      <div className="item-info">
                        <span className="item-title">{doc.document.title}</span>
                        <span
                          className="severity-badge"
                          style={{ backgroundColor: SEVERITY_COLORS[doc.risk_analysis.severity] }}
                        >
                          {doc.risk_analysis.overall_risk_score?.toFixed(0)}점
                        </span>
                      </div>
                      <FiChevronRight className="item-arrow" />
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Upcoming Schedule */}
        <div className="schedule-card">
          <div className="card-header">
            <div className="card-title">
              <FiCalendar className="card-icon" />
              <h3>다가오는 일정</h3>
            </div>
          </div>

          <div className="card-content">
            {upcomingSchedules.length === 0 ? (
              <div className="empty-state compact">
                <FiClock className="empty-icon" />
                <p>예정된 일정이 없습니다</p>
              </div>
            ) : (
              <div className="schedule-list">
                {upcomingSchedules.map((schedule, idx) => {
                  const daysUntil = Math.ceil(
                    (new Date(schedule.date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
                  );
                  const isUrgent = daysUntil <= 3;

                  return (
                    <div
                      key={`${schedule.caseId}-${idx}`}
                      className={`schedule-item ${isUrgent ? 'urgent' : ''}`}
                      onClick={() => navigate(`/cases-v2?caseId=${schedule.caseId}`)}
                    >
                      <div className="schedule-date-box">
                        <span className="schedule-day">
                          {new Date(schedule.date).getDate()}
                        </span>
                        <span className="schedule-month">
                          {new Date(schedule.date).toLocaleDateString('ko-KR', {
                            month: 'short',
                          })}
                        </span>
                      </div>
                      <div className="schedule-info">
                        <span className="schedule-title">{schedule.title}</span>
                        <span className="schedule-case">{schedule.caseName}</span>
                      </div>
                      {isUrgent && (
                        <span className="urgent-badge">
                          {daysUntil === 0 ? '오늘' : `D-${daysUntil}`}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="activity-card">
          <div className="card-header">
            <div className="card-title">
              <FiClock className="card-icon" />
              <h3>최근 활동</h3>
            </div>
          </div>

          <div className="card-content">
            {recentActivities.length === 0 ? (
              <div className="empty-state compact">
                <FiActivity className="empty-icon" />
                <p>최근 활동이 없습니다</p>
              </div>
            ) : (
              <div className="activity-list">
                {recentActivities.map((activity, idx) => (
                  <div key={idx} className="activity-item">
                    <div className={`activity-icon ${activity.type}`}>
                      {activity.icon}
                    </div>
                    <div className="activity-info">
                      <span className="activity-title">{activity.title}</span>
                      <span className="activity-subtitle">{activity.subtitle}</span>
                    </div>
                    <span className="activity-time">
                      {formatRelativeTime(activity.time)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <h3>빠른 시작</h3>
        <div className="actions-grid">
          <button className="action-btn" onClick={() => navigate('/agent-hub')}>
            <FiMessageSquare className="action-icon" />
            <span>AI 어시스턴트</span>
          </button>
          <button className="action-btn" onClick={() => navigate('/cases-v2')}>
            <FiFolder className="action-icon" />
            <span>사건 등록</span>
          </button>
          <button className="action-btn" onClick={() => navigate('/documents')}>
            <FiFileText className="action-icon" />
            <span>문서 업로드</span>
          </button>
          <button className="action-btn" onClick={() => navigate('/research')}>
            <FiTrendingUp className="action-icon" />
            <span>법률 리서치</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
