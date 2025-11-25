import React from 'react';
import { UserDocumentDetail, Summary, KeyClause } from '../types';
import DocumentMeta from './DocumentMeta';
import DocumentViewer from './DocumentViewer';
import AnalysisPanel from './AnalysisPanel';
import '../styles/DocumentDetailLayout.css';

interface DocumentDetailLayoutProps {
  document: UserDocumentDetail;
  token?: string;
  fileUrl?: string;
  onDelete: () => void;
  deleting: boolean;
  onBack: () => void;
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

const DocumentDetailLayout: React.FC<DocumentDetailLayoutProps> = ({
  document,
  token,
  fileUrl,
  onDelete,
  deleting,
  onBack,
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
  return (
    <div className="document-detail-layout">
      {/* Left Panel: Document Meta */}
      <aside className="layout-left">
        <DocumentMeta
          document={document}
          onDelete={onDelete}
          deleting={deleting}
          onBack={onBack}
        />
      </aside>

      {/* Center Panel: Document Viewer */}
      <main className="layout-center">
        <DocumentViewer document={document} fileUrl={fileUrl} />
      </main>

      {/* Right Panel: Analysis Results */}
      <aside className="layout-right">
        <AnalysisPanel
          document={document}
          token={token}
          summary={summary}
          summaryLoading={summaryLoading}
          summaryError={summaryError}
          onGenerateSummary={onGenerateSummary}
          generatingSummary={generatingSummary}
          clauses={clauses}
          clausesLoading={clausesLoading}
          clausesError={clausesError}
          onExtractClauses={onExtractClauses}
          extractingClauses={extractingClauses}
        />
      </aside>
    </div>
  );
};

export default DocumentDetailLayout;
