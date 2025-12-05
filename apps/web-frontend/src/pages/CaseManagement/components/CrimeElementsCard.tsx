import React from 'react';
import { FiCheckCircle, FiXCircle, FiTarget } from 'react-icons/fi';
import { CrimeElements } from '../../../types';
import './CriminalCards.css';

interface CrimeElementsCardProps {
  elements: CrimeElements;
}

const CrimeElementsCard: React.FC<CrimeElementsCardProps> = ({ elements }) => {
  const renderElement = (element: { element: string; description: string; fulfilled: boolean }, index: number) => (
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

  const objectiveFulfilled = elements.objective.filter(e => e.fulfilled).length;
  const subjectiveFulfilled = elements.subjective.filter(e => e.fulfilled).length;
  const totalFulfilled = objectiveFulfilled + subjectiveFulfilled;
  const total = elements.objective.length + elements.subjective.length;

  return (
    <div className="criminal-card crime-elements-card">
      <div className="card-header">
        <div className="card-title">
          <FiTarget className="card-icon" />
          <h4>구성요건 분석</h4>
        </div>
        <div className="fulfillment-summary">
          <span className={totalFulfilled === total ? 'all-fulfilled' : 'partial'}>
            {totalFulfilled}/{total} 충족
          </span>
        </div>
      </div>

      <div className="card-content">
        {elements.objective.length > 0 && (
          <div className="element-section">
            <h5>객관적 구성요건</h5>
            <div className="elements-list">
              {elements.objective.map((el, idx) => renderElement(el, idx))}
            </div>
          </div>
        )}

        {elements.subjective.length > 0 && (
          <div className="element-section">
            <h5>주관적 구성요건</h5>
            <div className="elements-list">
              {elements.subjective.map((el, idx) => renderElement(el, idx))}
            </div>
          </div>
        )}

        {elements.objective.length === 0 && elements.subjective.length === 0 && (
          <div className="no-data">구성요건 분석 데이터가 없습니다.</div>
        )}
      </div>
    </div>
  );
};

export default CrimeElementsCard;
