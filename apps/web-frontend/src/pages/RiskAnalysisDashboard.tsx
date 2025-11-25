import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import {
  RiskOverview,
  RiskDocumentListItem,
  RiskSeverity,
  SeverityDistribution,
  CategoryDistribution
} from '../types';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import RiskDocumentTable from '../components/RiskDocumentTable';
import '../styles/RiskAnalysisDashboard.css';

// Color mappings for severity
const SEVERITY_COLORS: Record<keyof SeverityDistribution, string> = {
  CRITICAL: '#dc2626',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#22c55e',
  INFO: '#3b82f6'
};

const SEVERITY_LABELS: Record<keyof SeverityDistribution, string> = {
  CRITICAL: '심각',
  HIGH: '높음',
  MEDIUM: '중간',
  LOW: '낮음',
  INFO: '정보'
};

// Color mappings for categories
const CATEGORY_COLORS: Record<keyof CategoryDistribution, string> = {
  LEGAL: '#8b5cf6',
  FINANCIAL: '#06b6d4',
  COMPLIANCE: '#f59e0b',
  OPERATIONAL: '#10b981',
  REPUTATIONAL: '#ec4899',
  OTHER: '#6b7280'
};

const CATEGORY_LABELS: Record<keyof CategoryDistribution, string> = {
  LEGAL: '법률',
  FINANCIAL: '재무',
  COMPLIANCE: '규정',
  OPERATIONAL: '운영',
  REPUTATIONAL: '평판',
  OTHER: '기타'
};

const RiskAnalysisDashboard: React.FC = () => {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [overview, setOverview] = useState<RiskOverview | null>(null);
  const [documents, setDocuments] = useState<RiskDocumentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [selectedSeverity, setSelectedSeverity] = useState<RiskSeverity | null>(null);
  const [sortBy, setSortBy] = useState<'risk_score' | 'created_at' | 'document_title'>('risk_score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 10;

  // Load overview data
  const loadOverview = useCallback(async () => {
    if (!token) return;

    try {
      const data = await apiClient.getRiskOverview(token);
      setOverview(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load risk overview');
    }
  }, [token]);

  // Load documents with risk
  const loadDocuments = useCallback(async () => {
    if (!token) return;

    setDocumentsLoading(true);

    try {
      const data = await apiClient.getDocumentsWithRisk({
        page,
        page_size: pageSize,
        severity: selectedSeverity || undefined,
        sort_by: sortBy,
        sort_order: sortOrder
      }, token);

      setDocuments(data.results);
      setTotalPages(data.total_pages);
      setTotalCount(data.count);
    } catch (err: any) {
      setError(err.message || 'Failed to load documents');
    } finally {
      setDocumentsLoading(false);
    }
  }, [token, page, selectedSeverity, sortBy, sortOrder]);

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await loadOverview();
      setLoading(false);
    };
    loadData();
  }, [loadOverview]);

  // Load documents when filters change
  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [selectedSeverity, sortBy, sortOrder]);

  // Prepare chart data
  const severityChartData = overview
    ? Object.entries(overview.severity_distribution)
        .filter(([_, value]) => value > 0)
        .map(([key, value]) => ({
          name: SEVERITY_LABELS[key as keyof SeverityDistribution],
          value,
          color: SEVERITY_COLORS[key as keyof SeverityDistribution]
        }))
    : [];

  const categoryChartData = overview
    ? Object.entries(overview.category_distribution)
        .filter(([_, value]) => value > 0)
        .map(([key, value]) => ({
          name: CATEGORY_LABELS[key as keyof CategoryDistribution],
          value,
          fill: CATEGORY_COLORS[key as keyof CategoryDistribution]
        }))
    : [];

  // Handle severity filter click
  const handleSeverityFilter = (severity: RiskSeverity | null) => {
    setSelectedSeverity(prev => prev === severity ? null : severity);
  };

  // Handle sort change
  const handleSortChange = (newSortBy: typeof sortBy) => {
    if (sortBy === newSortBy) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(newSortBy);
      setSortOrder('desc');
    }
  };

  // Navigate to document detail
  const handleDocumentClick = (documentId: string) => {
    navigate(`/documents/${documentId}`);
  };

  if (loading) {
    return (
      <div className="risk-dashboard">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>리스크 데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="risk-dashboard">
        <div className="error-container">
          <p className="error-message">{error}</p>
          <button onClick={() => window.location.reload()} className="btn-primary">
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="risk-dashboard">
      <div className="dashboard-header">
        <h1>리스크 분석 대시보드</h1>
        <p className="dashboard-subtitle">문서별 위험 요소 분석 및 통계</p>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon total">📄</div>
          <div className="stat-content">
            <div className="stat-value">{overview?.total_documents || 0}</div>
            <div className="stat-label">전체 문서</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon with-risk">⚠️</div>
          <div className="stat-content">
            <div className="stat-value">{overview?.documents_with_risk || 0}</div>
            <div className="stat-label">분석 완료 문서</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon high-risk">🔴</div>
          <div className="stat-content">
            <div className="stat-value">{overview?.high_risk_count || 0}</div>
            <div className="stat-label">고위험 문서</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon avg-score">📊</div>
          <div className="stat-content">
            <div className="stat-value">
              {overview?.avg_risk_score?.toFixed(1) || '0.0'}
            </div>
            <div className="stat-label">평균 위험 점수</div>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="charts-section">
        {/* Severity Distribution Pie Chart */}
        <div className="chart-card">
          <h3>심각도별 분포</h3>
          {severityChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={severityChartData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                  }
                >
                  {severityChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="no-data">분석된 문서가 없습니다</div>
          )}
        </div>

        {/* Category Distribution Bar Chart */}
        <div className="chart-card">
          <h3>카테고리별 리스크</h3>
          {categoryChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={categoryChartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={60} />
                <Tooltip />
                <Bar dataKey="value" name="건수" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="no-data">분석된 문서가 없습니다</div>
          )}
        </div>
      </div>

      {/* Filter Section */}
      <div className="filter-section">
        <h3>심각도 필터</h3>
        <div className="severity-filters">
          {(Object.keys(SEVERITY_LABELS) as RiskSeverity[]).map(severity => (
            <button
              key={severity}
              className={`severity-btn ${selectedSeverity === severity ? 'active' : ''}`}
              style={{
                '--severity-color': SEVERITY_COLORS[severity]
              } as React.CSSProperties}
              onClick={() => handleSeverityFilter(severity)}
            >
              {SEVERITY_LABELS[severity]}
              {overview?.severity_distribution && (
                <span className="count">
                  {overview.severity_distribution[severity]}
                </span>
              )}
            </button>
          ))}
          {selectedSeverity && (
            <button
              className="severity-btn clear-btn"
              onClick={() => setSelectedSeverity(null)}
            >
              필터 초기화
            </button>
          )}
        </div>
      </div>

      {/* Documents Table */}
      <div className="documents-section">
        <div className="section-header">
          <h3>
            위험 분석 문서 목록
            {totalCount > 0 && <span className="count">({totalCount}건)</span>}
          </h3>
          <div className="sort-controls">
            <label>정렬:</label>
            <select
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [newSortBy, newSortOrder] = e.target.value.split('-') as [typeof sortBy, typeof sortOrder];
                setSortBy(newSortBy);
                setSortOrder(newSortOrder);
              }}
            >
              <option value="risk_score-desc">위험 점수 높은 순</option>
              <option value="risk_score-asc">위험 점수 낮은 순</option>
              <option value="created_at-desc">최신 분석순</option>
              <option value="created_at-asc">오래된 분석순</option>
              <option value="document_title-asc">문서명 오름차순</option>
              <option value="document_title-desc">문서명 내림차순</option>
            </select>
          </div>
        </div>

        <RiskDocumentTable
          documents={documents}
          loading={documentsLoading}
          onDocumentClick={handleDocumentClick}
          onSortChange={handleSortChange}
          sortBy={sortBy}
          sortOrder={sortOrder}
        />

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <button
              className="pagination-btn"
              disabled={page === 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
            >
              이전
            </button>
            <span className="page-info">
              {page} / {totalPages}
            </span>
            <button
              className="pagination-btn"
              disabled={page === totalPages}
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            >
              다음
            </button>
          </div>
        )}
      </div>

      {/* Recent Analyses */}
      {overview?.recent_analyses && overview.recent_analyses.length > 0 && (
        <div className="recent-section">
          <h3>최근 분석 문서</h3>
          <div className="recent-list">
            {overview.recent_analyses.map((analysis) => (
              <div
                key={analysis.id}
                className="recent-item"
                onClick={() => handleDocumentClick(analysis.document_id)}
              >
                <div className="recent-info">
                  <span className="recent-title">{analysis.document_title}</span>
                  <span className="recent-date">
                    {new Date(analysis.created_at).toLocaleDateString('ko-KR')}
                  </span>
                </div>
                <div className="recent-risk">
                  <span
                    className="severity-badge"
                    style={{
                      backgroundColor: SEVERITY_COLORS[analysis.severity]
                    }}
                  >
                    {SEVERITY_LABELS[analysis.severity]}
                  </span>
                  <span className="risk-score">
                    {analysis.overall_risk_score.toFixed(1)}점
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default RiskAnalysisDashboard;
