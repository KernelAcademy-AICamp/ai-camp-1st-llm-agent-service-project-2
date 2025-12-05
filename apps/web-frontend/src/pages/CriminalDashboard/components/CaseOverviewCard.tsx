import React from 'react';
import { useNavigate } from 'react-router-dom';
import { CriminalCase } from '../../../types';
import { FiFolder, FiClock, FiCheckCircle, FiArrowRight } from 'react-icons/fi';

interface CaseOverviewCardProps {
  cases: CriminalCase[];
}

const CaseOverviewCard: React.FC<CaseOverviewCardProps> = ({ cases }) => {
  const navigate = useNavigate();

  // 통계 계산
  const totalCases = cases.length;
  const activeCases = cases.filter(c => c.stage !== 'CLOSED').length;
  const closedCases = cases.filter(c => c.stage === 'CLOSED').length;

  // 최근 등록 사건 (최대 3개)
  const recentCases = [...cases]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 3);

  // 총 문서 수
  const totalDocuments = cases.reduce((sum, c) => sum + (c.uploaded_files?.length || 0), 0);

  const handleGoToCases = () => {
    navigate('/cases-v2');
  };

  return (
    <div className="case-overview-card">
      <div className="overview-header">
        <h4 className="card-title">사건 현황</h4>
        <button className="link-btn" onClick={handleGoToCases}>
          전체 보기 <FiArrowRight />
        </button>
      </div>

      {/* 숫자 요약 */}
      <div className="overview-stats">
        <div className="stat-item total">
          <FiFolder className="stat-icon" />
          <div className="stat-content">
            <span className="stat-value">{totalCases}</span>
            <span className="stat-label">전체 사건</span>
          </div>
        </div>

        <div className="stat-item active">
          <FiClock className="stat-icon" />
          <div className="stat-content">
            <span className="stat-value">{activeCases}</span>
            <span className="stat-label">진행 중</span>
          </div>
        </div>

        <div className="stat-item closed">
          <FiCheckCircle className="stat-icon" />
          <div className="stat-content">
            <span className="stat-value">{closedCases}</span>
            <span className="stat-label">종결</span>
          </div>
        </div>
      </div>

      {/* 총 문서 수 */}
      <div className="documents-summary">
        <span className="doc-count">{totalDocuments}개</span>
        <span className="doc-label">업로드된 문서</span>
      </div>

      {/* 최근 사건 미니 리스트 */}
      {recentCases.length > 0 && (
        <div className="recent-cases">
          <h5>최근 등록</h5>
          <ul>
            {recentCases.map((c) => (
              <li key={c.id} onClick={() => navigate(`/cases-v2/${c.id}`)}>
                <span className="case-name">{c.case_name}</span>
                <span className="case-date">
                  {new Date(c.created_at).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default CaseOverviewCard;
