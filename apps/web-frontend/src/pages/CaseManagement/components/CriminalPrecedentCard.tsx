import React, { useState } from 'react';
import { FiBook, FiCalendar, FiMapPin } from 'react-icons/fi';
import { CriminalPrecedent } from '../../../types';
import SourceDetailModal from '../../../components/SourceDetailModal/SourceDetailModal';
import './CriminalPrecedentCard.css';

interface CriminalPrecedentCardProps {
  precedents: CriminalPrecedent[];
}

const CriminalPrecedentCard: React.FC<CriminalPrecedentCardProps> = ({ precedents }) => {
  const [selectedPrecedent, setSelectedPrecedent] = useState<CriminalPrecedent | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  if (!precedents || precedents.length === 0) {
    return null;
  }

  const handlePrecedentClick = (precedent: CriminalPrecedent) => {
    setSelectedPrecedent(precedent);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedPrecedent(null);
  };

  // CriminalPrecedent를 SourceDetailModal props 형식으로 변환
  const convertToSourceFormat = (precedent: CriminalPrecedent | null) => {
    if (!precedent) return null;
    return {
      title: precedent.case_number,
      case_number: precedent.case_number,
      court: precedent.court,
      date: precedent.date,
      doc_type: `판례 (${precedent.crime_type || '형사'})`,
      text_snippet: precedent.summary,
      relevance_score: precedent.relevance / 100, // 0~100 → 0~1 변환
    };
  };

  const getScoreColor = (relevance: number) => {
    if (relevance >= 70) return 'score-high';
    if (relevance >= 40) return 'score-medium';
    return 'score-low';
  };

  const getScoreLabel = (relevance: number) => {
    if (relevance >= 70) return '최고 관련';
    if (relevance >= 40) return '높은 관련';
    return '관련';
  };

  return (
    <div className="precedent-section">
      {/* 헤더 - LegalResearch sources-header 스타일 */}
      <div className="precedent-section-header">
        <h3>관련 판례 ({precedents.length}건)</h3>
        <p className="precedent-section-description">
          유사 사건의 판례를 AI가 분석하여 관련도순으로 정렬했습니다
        </p>
      </div>

      {/* 판례 목록 - LegalResearch sources-list 스타일 */}
      <div className="precedent-list">
        {precedents.map((precedent, idx) => (
          <div
            key={idx}
            className={`precedent-card ${getScoreColor(precedent.relevance)}`}
            onClick={() => handlePrecedentClick(precedent)}
            style={{ cursor: 'pointer' }}
          >
            {/* 헤더 영역 */}
            <div className="precedent-card-header">
              <div className="precedent-rank">#{idx + 1}</div>
              <div className="precedent-title-wrapper">
                <span className="precedent-type-icon">
                  <FiBook />
                </span>
                <h4 className="precedent-title">
                  {precedent.case_number || '사건번호 미상'}
                </h4>
              </div>
              <div className="precedent-meta">
                <span className="precedent-type-label">판례</span>
                {precedent.crime_type && (
                  <span className="precedent-crime-type">{precedent.crime_type}</span>
                )}
                <span className={`precedent-score ${getScoreColor(precedent.relevance)}`}>
                  {getScoreLabel(precedent.relevance)}
                </span>
              </div>
            </div>

            {/* 선고 형량 */}
            {precedent.sentence && (
              <div className="precedent-sentence">
                <span className="sentence-label">선고:</span>
                <span className="sentence-value">{precedent.sentence}</span>
              </div>
            )}

            {/* 요약 */}
            <p className="precedent-snippet">
              {precedent.summary || '판결 요약이 제공되지 않았습니다.'}
            </p>

            {/* 푸터 */}
            <div className="precedent-footer">
              {precedent.court && (
                <span className="precedent-court">
                  <FiMapPin /> {precedent.court}
                </span>
              )}
              {precedent.date && (
                <span className="precedent-date">
                  <FiCalendar /> {precedent.date}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* 판례 상세 모달 */}
      <SourceDetailModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        source={convertToSourceFormat(selectedPrecedent)}
      />
    </div>
  );
};

export default CriminalPrecedentCard;
