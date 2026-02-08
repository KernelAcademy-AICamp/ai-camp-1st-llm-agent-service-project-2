import React from 'react';
import { RiskDocumentListItem, RiskSeverity } from '../types';
import '../styles/RiskDocumentTable.css';

// Severity configuration
const SEVERITY_CONFIG: Record<RiskSeverity, { label: string; color: string; bgColor: string }> = {
  CRITICAL: { label: '심각', color: '#dc2626', bgColor: '#fef2f2' },
  HIGH: { label: '높음', color: '#f97316', bgColor: '#fff7ed' },
  MEDIUM: { label: '중간', color: '#eab308', bgColor: '#fefce8' },
  LOW: { label: '낮음', color: '#22c55e', bgColor: '#f0fdf4' },
  INFO: { label: '정보', color: '#3b82f6', bgColor: '#eff6ff' }
};

interface RiskDocumentTableProps {
  documents: RiskDocumentListItem[];
  loading: boolean;
  onDocumentClick: (documentId: string) => void;
  onSortChange: (sortBy: 'risk_score' | 'created_at' | 'document_title') => void;
  sortBy: 'risk_score' | 'created_at' | 'document_title';
  sortOrder: 'asc' | 'desc';
}

const RiskDocumentTable: React.FC<RiskDocumentTableProps> = ({
  documents,
  loading,
  onDocumentClick,
  onSortChange,
  sortBy,
  sortOrder
}) => {
  // Get sort indicator
  const getSortIndicator = (column: typeof sortBy) => {
    if (sortBy !== column) return '';
    return sortOrder === 'asc' ? ' ↑' : ' ↓';
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  // Get risk score color based on value
  const getRiskScoreColor = (score: number) => {
    if (score >= 80) return '#dc2626';
    if (score >= 60) return '#f97316';
    if (score >= 40) return '#eab308';
    if (score >= 20) return '#22c55e';
    return '#3b82f6';
  };

  if (loading) {
    return (
      <div className="risk-table-container">
        <div className="table-loading">
          <div className="loading-spinner"></div>
          <p>문서를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="risk-table-container">
        <div className="table-empty">
          <p>해당하는 문서가 없습니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="risk-table-container">
      <table className="risk-table">
        <thead>
          <tr>
            <th
              className={`sortable ${sortBy === 'document_title' ? 'active' : ''}`}
              onClick={() => onSortChange('document_title')}
            >
              문서명{getSortIndicator('document_title')}
            </th>
            <th>문서 유형</th>
            <th
              className={`sortable ${sortBy === 'risk_score' ? 'active' : ''}`}
              onClick={() => onSortChange('risk_score')}
            >
              위험 점수{getSortIndicator('risk_score')}
            </th>
            <th>심각도</th>
            <th>위험 항목</th>
            <th>분석 모델</th>
            <th
              className={`sortable ${sortBy === 'created_at' ? 'active' : ''}`}
              onClick={() => onSortChange('created_at')}
            >
              분석 일시{getSortIndicator('created_at')}
            </th>
          </tr>
        </thead>
        <tbody>
          {documents.map((item) => {
            const severityConfig = SEVERITY_CONFIG[item.risk_analysis.severity];

            return (
              <tr
                key={item.document.id}
                onClick={() => onDocumentClick(item.document.id)}
                className="clickable-row"
              >
                <td className="document-title">
                  <span className="title-text">{item.document.title}</span>
                </td>
                <td>
                  <span className="doc-type-badge">
                    {item.document.doc_type}
                  </span>
                </td>
                <td className="risk-score-cell">
                  <div className="risk-score-container">
                    <div
                      className="risk-score-bar"
                      style={{
                        width: `${item.risk_analysis.overall_risk_score}%`,
                        backgroundColor: getRiskScoreColor(item.risk_analysis.overall_risk_score)
                      }}
                    />
                    <span className="risk-score-value">
                      {item.risk_analysis.overall_risk_score.toFixed(1)}
                    </span>
                  </div>
                </td>
                <td>
                  <span
                    className="severity-badge"
                    style={{
                      color: severityConfig.color,
                      backgroundColor: severityConfig.bgColor,
                      borderColor: severityConfig.color
                    }}
                  >
                    {severityConfig.label}
                  </span>
                </td>
                <td className="risk-item-count">
                  {item.risk_analysis.risk_item_count}건
                </td>
                <td className="llm-model">
                  <span className="model-badge">
                    {item.risk_analysis.llm_model}
                  </span>
                </td>
                <td className="analysis-date">
                  {formatDate(item.risk_analysis.created_at)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default RiskDocumentTable;
