import React, { useState } from 'react';
import { UserDocumentDetail, Summary, KeyClause } from '../types';
import SummarySection from './SummarySection';
import ClauseList from './ClauseList';
import RiskAnalysisSection from './RiskAnalysisSection';
import CaseAnalysisSection from './CaseAnalysisSection';
import ModelComparisonSection from './ModelComparisonSection';
import '../styles/AnalysisPanel.css';

type TabType = 'summary' | 'clauses' | 'risk' | 'case' | 'model';

interface AnalysisPanelProps {
  document: UserDocumentDetail;
  token?: string;
  // Summary props
  summary: Summary | null;
  summaryLoading: boolean;
  summaryError: string | null;
  onGenerateSummary: () => void;
  generatingSummary: boolean;
  // Clauses props
  clauses: KeyClause[];
  clausesLoading: boolean;
  clausesError: string | null;
  onExtractClauses: () => void;
  extractingClauses: boolean;
}

const AnalysisPanel: React.FC<AnalysisPanelProps> = ({
  document,
  token,
  summary,
  summaryLoading,
  summaryError,
  onGenerateSummary,
  generatingSummary,
  clauses,
  clausesLoading,
  clausesError,
  onExtractClauses,
  extractingClauses,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('summary');

  const isCaseDocument = document.doc_type === 'CASE';

  // Tab configuration
  const tabs: { id: TabType; label: string; show: boolean }[] = [
    { id: 'summary', label: '요약', show: true },
    { id: 'clauses', label: '조항', show: true },
    { id: 'risk', label: '리스크', show: true },
    { id: 'case', label: '사건분석', show: isCaseDocument },
    { id: 'model', label: '모델비교', show: true },
  ];

  const visibleTabs = tabs.filter((tab) => tab.show);

  // Get document text for model comparison
  const documentText =
    document.chunks && document.chunks.length > 0
      ? document.chunks.map((c) => c.text).join('\n\n')
      : undefined;

  const renderTabContent = () => {
    switch (activeTab) {
      case 'summary':
        return (
          <SummarySection
            summary={summary}
            loading={summaryLoading}
            error={summaryError}
            onGenerate={onGenerateSummary}
            generating={generatingSummary}
          />
        );

      case 'clauses':
        return (
          <ClauseList
            clauses={clauses}
            loading={clausesLoading}
            error={clausesError}
            onExtract={onExtractClauses}
            extracting={extractingClauses}
          />
        );

      case 'risk':
        return (
          <RiskAnalysisSection
            documentId={document.id}
            token={token}
            documentTitle={document.title}
          />
        );

      case 'case':
        if (!isCaseDocument) return null;
        return (
          <CaseAnalysisSection
            documentId={document.id}
            token={token}
            documentTitle={document.title}
          />
        );

      case 'model':
        return (
          <ModelComparisonSection
            documentId={document.id}
            documentTitle={document.title}
            documentText={documentText}
            token={token}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="analysis-panel">
      <div className="panel-header">
        <h3>AI 분석</h3>
      </div>

      <div className="panel-tabs">
        {visibleTabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="panel-content">{renderTabContent()}</div>
    </div>
  );
};

export default AnalysisPanel;
