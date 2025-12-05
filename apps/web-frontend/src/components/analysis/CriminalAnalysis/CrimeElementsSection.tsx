import React, { useState, useEffect, useCallback } from 'react';
import { FiCheckCircle, FiXCircle, FiTarget, FiRefreshCw } from 'react-icons/fi';
import { CrimeElements, CrimeElement } from '../../../types';
import { apiClient } from '../../../api/client';
import './CriminalAnalysis.css';

interface CrimeElementsSectionProps {
  documentId: string;
  token?: string;
  crimeType?: string;
  // Pre-loaded data (optional)
  initialElements?: CrimeElements;
}

const CrimeElementsSection: React.FC<CrimeElementsSectionProps> = ({
  documentId,
  token,
  crimeType,
  initialElements
}) => {
  const [elements, setElements] = useState<CrimeElements | null>(initialElements || null);
  const [loading, setLoading] = useState(!initialElements);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const loadElements = useCallback(async () => {
    if (!documentId || !token) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getCriminalAnalysis(documentId, token);
      if (response.crime_elements) {
        setElements(response.crime_elements);
      }
    } catch (err: any) {
      // If no analysis exists yet, that's okay
      console.log('No criminal elements found for document:', documentId);
    } finally {
      setLoading(false);
    }
  }, [documentId, token]);

  useEffect(() => {
    if (!initialElements) {
      loadElements();
    }
  }, [loadElements, initialElements]);

  const handleAnalyze = async () => {
    if (!documentId || !token) return;

    setAnalyzing(true);
    setError(null);

    try {
      const response = await apiClient.analyzeCriminalDocument(documentId, token);
      if (response.crime_elements) {
        setElements(response.crime_elements);
      }
    } catch (err: any) {
      setError(err.message || '구성요건 분석에 실패했습니다.');
    } finally {
      setAnalyzing(false);
    }
  };

  const renderElement = (element: CrimeElement, index: number) => (
    <div key={index} className={`element-item ${element.fulfilled ? 'fulfilled' : 'not-fulfilled'}`}>
      <div className="element-icon">
        {element.fulfilled ? (
          <FiCheckCircle className="icon-fulfilled" />
        ) : (
          <FiXCircle className="icon-not-fulfilled" />
        )}
      </div>
      <div className="element-content">
        <span className="element-name">{element.element}</span>
        <span className="element-desc">{element.description}</span>
      </div>
      <span className={`element-status ${element.fulfilled ? 'status-fulfilled' : 'status-not-fulfilled'}`}>
        {element.fulfilled ? '충족' : '미충족'}
      </span>
    </div>
  );

  if (loading) {
    return (
      <div className="criminal-section crime-elements-section">
        <div className="section-header">
          <div className="section-title">
            <FiTarget className="section-icon" />
            <h3>{crimeType ? `${crimeType} ` : ''}구성요건 분석</h3>
          </div>
        </div>
        <div className="section-content">
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>구성요건 분석 데이터를 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!elements) {
    return (
      <div className="criminal-section crime-elements-section">
        <div className="section-header">
          <div className="section-title">
            <FiTarget className="section-icon" />
            <h3>{crimeType ? `${crimeType} ` : ''}구성요건 분석</h3>
          </div>
        </div>
        <div className="section-content">
          <div className="empty-state">
            <FiTarget className="empty-icon" />
            <p>아직 구성요건 분석이 수행되지 않았습니다.</p>
            <button
              className="btn-analyze"
              onClick={handleAnalyze}
              disabled={analyzing}
            >
              {analyzing ? (
                <>
                  <FiRefreshCw className="icon-spin" />
                  분석 중...
                </>
              ) : (
                '구성요건 분석하기'
              )}
            </button>
            {error && <p className="error-message">{error}</p>}
          </div>
        </div>
      </div>
    );
  }

  const objectiveFulfilled = elements.objective.filter(e => e.fulfilled).length;
  const subjectiveFulfilled = elements.subjective.filter(e => e.fulfilled).length;
  const totalFulfilled = objectiveFulfilled + subjectiveFulfilled;
  const total = elements.objective.length + elements.subjective.length;

  return (
    <div className="criminal-section crime-elements-section">
      <div className="section-header">
        <div className="section-title">
          <FiTarget className="section-icon" />
          <h3>{crimeType ? `${crimeType} ` : ''}구성요건 분석</h3>
        </div>
        <div className="fulfillment-summary">
          <span className={totalFulfilled === total ? 'all-fulfilled' : 'partial'}>
            {totalFulfilled}/{total} 충족
          </span>
        </div>
      </div>

      <div className="section-content">
        {elements.objective.length > 0 && (
          <div className="element-group">
            <h4>객관적 구성요건</h4>
            <div className="elements-list">
              {elements.objective.map((el, idx) => renderElement(el, idx))}
            </div>
          </div>
        )}

        {elements.subjective.length > 0 && (
          <div className="element-group">
            <h4>주관적 구성요건</h4>
            <div className="elements-list">
              {elements.subjective.map((el, idx) => renderElement(el, idx))}
            </div>
          </div>
        )}

        {elements.objective.length === 0 && elements.subjective.length === 0 && (
          <div className="no-data">구성요건 분석 데이터가 없습니다.</div>
        )}

        <button
          className="btn-refresh"
          onClick={handleAnalyze}
          disabled={analyzing}
        >
          {analyzing ? (
            <>
              <FiRefreshCw className="icon-spin" />
              재분석 중...
            </>
          ) : (
            <>
              <FiRefreshCw />
              재분석
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default CrimeElementsSection;
