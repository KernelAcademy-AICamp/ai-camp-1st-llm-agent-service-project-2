import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CriminalCase,
  CriminalStage,
  CRIMINAL_STAGE_LABELS
} from '../../../types';
import {
  FiCalendar,
  FiChevronDown,
  FiChevronUp,
  FiEye,
  FiAlertTriangle
} from 'react-icons/fi';

interface CaseListTableProps {
  cases: CriminalCase[];
  onViewCase?: (caseId: string) => void;
}

// 정렬 옵션 타입
type SortField = 'next_schedule' | 'stage' | 'created_at';
type SortOrder = 'asc' | 'desc';

// 단계별 우선순위 (숫자가 낮을수록 우선)
const STAGE_PRIORITY: Record<CriminalStage, number> = {
  TRIAL: 1,
  PROSECUTION: 2,
  INVESTIGATION: 3,
  COMPLAINT: 4,
  JUDGMENT: 5,
  CLOSED: 6,
};

// 단계별 색상
const STAGE_COLORS: Record<CriminalStage, string> = {
  COMPLAINT: '#f59e0b',
  INVESTIGATION: '#3b82f6',
  PROSECUTION: '#8b5cf6',
  TRIAL: '#ec4899',
  JUDGMENT: '#10b981',
  CLOSED: '#6b7280',
};

const CaseListTable: React.FC<CaseListTableProps> = ({ cases, onViewCase }) => {
  const navigate = useNavigate();
  const [sortField, setSortField] = useState<SortField>('next_schedule');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // 정렬 핸들러
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  // 정렬 아이콘
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortOrder === 'asc' ? <FiChevronUp /> : <FiChevronDown />;
  };

  // 다음 일정 추출
  const getNextSchedule = (caseData: CriminalCase) => {
    const upcoming = (caseData.schedules || [])
      .filter(s => !s.is_completed)
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    return upcoming[0] || null;
  };

  // 정렬된 사건 목록
  const sortedCases = [...cases].sort((a, b) => {
    let comparison = 0;

    switch (sortField) {
      case 'next_schedule': {
        const scheduleA = getNextSchedule(a);
        const scheduleB = getNextSchedule(b);
        const dateA = scheduleA ? new Date(scheduleA.date).getTime() : Infinity;
        const dateB = scheduleB ? new Date(scheduleB.date).getTime() : Infinity;
        comparison = dateA - dateB;
        break;
      }
      case 'stage': {
        const priorityA = a.stage ? STAGE_PRIORITY[a.stage] : 99;
        const priorityB = b.stage ? STAGE_PRIORITY[b.stage] : 99;
        comparison = priorityA - priorityB;
        break;
      }
      case 'created_at': {
        const timeA = new Date(a.created_at).getTime();
        const timeB = new Date(b.created_at).getTime();
        comparison = timeB - timeA; // 최신순 기본
        break;
      }
    }

    return sortOrder === 'asc' ? comparison : -comparison;
  });

  // 긴급 표시 여부 (3일 이내 일정)
  const isUrgent = (schedule: { date: string } | null) => {
    if (!schedule) return false;
    const daysUntil = Math.ceil(
      (new Date(schedule.date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    );
    return daysUntil <= 3 && daysUntil >= 0;
  };

  // 날짜 포맷
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  };

  const handleViewClick = (caseId: string) => {
    if (onViewCase) {
      onViewCase(caseId);
    } else {
      navigate(`/cases-v2?caseId=${caseId}`);
    }
  };

  return (
    <div className="case-list-table">
      <h4 className="card-title">전체 사건 목록</h4>

      <table className="cases-table">
        <thead>
          <tr>
            <th>사건명</th>
            <th>유형</th>
            <th
              className="sortable"
              onClick={() => handleSort('stage')}
            >
              단계 <SortIcon field="stage" />
            </th>
            <th
              className="sortable"
              onClick={() => handleSort('next_schedule')}
            >
              다음 일정 <SortIcon field="next_schedule" />
            </th>
            <th>상태</th>
            <th>액션</th>
          </tr>
        </thead>
        <tbody>
          {sortedCases.map((caseData) => {
            const nextSchedule = getNextSchedule(caseData);
            const urgent = isUrgent(nextSchedule);

            return (
              <tr key={caseData.id} className={urgent ? 'urgent' : ''}>
                <td className="case-name-cell">
                  <span className="case-name">{caseData.case_name}</span>
                </td>
                <td>
                  <span className="crime-type-badge small">
                    {caseData.crime_type || '-'}
                  </span>
                </td>
                <td>
                  {caseData.stage && (
                    <span
                      className="stage-badge small"
                      style={{
                        backgroundColor: `${STAGE_COLORS[caseData.stage]}20`,
                        color: STAGE_COLORS[caseData.stage],
                      }}
                    >
                      {CRIMINAL_STAGE_LABELS[caseData.stage]}
                    </span>
                  )}
                </td>
                <td>
                  {nextSchedule ? (
                    <span className="schedule-cell">
                      <FiCalendar />
                      {formatDate(nextSchedule.date)} {nextSchedule.title}
                    </span>
                  ) : (
                    <span className="no-schedule">-</span>
                  )}
                </td>
                <td>
                  {urgent ? (
                    <span className="status-badge urgent">
                      <FiAlertTriangle /> 주의
                    </span>
                  ) : (
                    <span className="status-badge normal">진행중</span>
                  )}
                </td>
                <td>
                  <button
                    className="btn-icon small"
                    onClick={() => handleViewClick(caseData.id)}
                    title="상세 보기"
                  >
                    <FiEye />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default CaseListTable;
