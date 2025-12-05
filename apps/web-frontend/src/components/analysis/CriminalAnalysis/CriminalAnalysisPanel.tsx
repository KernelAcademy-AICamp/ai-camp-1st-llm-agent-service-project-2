import React, { useState } from 'react';
import { FiFileText, FiTarget, FiBarChart2, FiBookOpen } from 'react-icons/fi';
import { UserDocumentDetail, AnalysisStatus } from '../../../types';
import JudgmentSummarySection from './JudgmentSummarySection';
import CrimeElementsSection from './CrimeElementsSection';
import SentencingSection from './SentencingSection';
import RelatedCasesSection from './RelatedCasesSection';
import ModelComparisonSection from '../../ModelComparisonSection';
import './CriminalAnalysis.css';

type CriminalTabType = 'judgment' | 'elements' | 'sentencing' | 'precedents' | 'model';

interface CriminalAnalysisPanelProps {
  document: UserDocumentDetail;
  token?: string;
  crimeType?: string;
  analysisStatus?: AnalysisStatus;
}

const CriminalAnalysisPanel: React.FC<CriminalAnalysisPanelProps> = ({
  document,
  token,
  crimeType,
  analysisStatus
}) => {
  const [activeTab, setActiveTab] = useState<CriminalTabType>('judgment');

  // Tab configuration for criminal documents
  const tabs: { id: CriminalTabType; label: string; icon: React.ReactNode }[] = [
    { id: 'judgment', label: '판시사항', icon: <FiFileText /> },
    { id: 'elements', label: '구성요건', icon: <FiTarget /> },
    { id: 'sentencing', label: '양형분석', icon: <FiBarChart2 /> },
    { id: 'precedents', label: '유사판례', icon: <FiBookOpen /> },
    { id: 'model', label: '모델비교', icon: null }
  ];

  // Get document text for model comparison
  const documentText =
    document.chunks && document.chunks.length > 0
      ? document.chunks.map((c) => c.text).join('\n\n')
      : undefined;

  const renderTabContent = () => {
    switch (activeTab) {
      case 'judgment':
        return (
          <JudgmentSummarySection
            documentId={document.id}
            token={token}
          />
        );

      case 'elements':
        return (
          <CrimeElementsSection
            documentId={document.id}
            token={token}
            crimeType={crimeType}
          />
        );

      case 'sentencing':
        return (
          <SentencingSection
            documentId={document.id}
            token={token}
          />
        );

      case 'precedents':
        return (
          <RelatedCasesSection
            documentId={document.id}
            token={token}
            crimeType={crimeType}
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
    <div className="criminal-analysis-panel">
      <div className="panel-header">
        <h2>형사문서 분석</h2>
        {crimeType && (
          <div className="crime-type-indicator">
            <FiTarget />
            <span>{crimeType}</span>
          </div>
        )}
      </div>

      <div className="criminal-analysis-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {renderTabContent()}
      </div>
    </div>
  );
};

export default CriminalAnalysisPanel;
