import React from 'react';
import {
  CriminalCase,
  CriminalScheduleItem,
  CriminalRecommendation
} from '../../../types';
import {
  FiCalendar,
  FiClock,
  FiAlertTriangle,
  FiCheckSquare,
  FiUsers,
  FiFileText
} from 'react-icons/fi';

interface UpcomingScheduleProps {
  cases: CriminalCase[];
  recommendations?: CriminalRecommendation[];
}

// 일정 타입별 아이콘
const SCHEDULE_ICONS: Record<string, React.ReactNode> = {
  HEARING: <FiCalendar />,
  SUBMISSION: <FiFileText />,
  MEETING: <FiUsers />,
  DEADLINE: <FiClock />,
  POLICE: <FiUsers />,
  PROSECUTOR: <FiUsers />,
};

// 우선순위 색상
const PRIORITY_COLORS: Record<string, string> = {
  HIGH: '#ef4444',
  MEDIUM: '#f59e0b',
  LOW: '#10b981',
};

const UpcomingSchedule: React.FC<UpcomingScheduleProps> = ({
  cases,
  recommendations = []
}) => {
  // 모든 사건의 일정을 병합하고 날짜순 정렬
  const allSchedules: (CriminalScheduleItem & { caseName?: string })[] = cases
    .flatMap(c =>
      (c.schedules || [])
        .filter(s => !s.is_completed)
        .map(s => ({ ...s, caseName: c.case_name }))
    )
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    .slice(0, 5); // 최대 5개 표시

  // 날짜 포맷팅
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

    const monthDay = `${date.getMonth() + 1}/${date.getDate()}`;

    if (diffDays === 0) return { display: '오늘', highlight: true };
    if (diffDays === 1) return { display: '내일', highlight: true };
    if (diffDays < 7) return { display: `${diffDays}일 후 (${monthDay})`, highlight: true };
    return { display: monthDay, highlight: false };
  };

  return (
    <div className="upcoming-schedule">
      <h4 className="card-title">
        <FiCalendar /> 다가오는 일정
      </h4>

      {/* 일정 목록 */}
      <div className="schedule-list">
        {allSchedules.length === 0 ? (
          <p className="no-schedule">예정된 일정이 없습니다.</p>
        ) : (
          allSchedules.map((schedule, index) => {
            const { display, highlight } = formatDate(schedule.date);
            return (
              <div
                key={index}
                className={`schedule-item ${highlight ? 'urgent' : ''}`}
              >
                <div className="schedule-icon">
                  {SCHEDULE_ICONS[schedule.schedule_type] || <FiCalendar />}
                </div>
                <div className="schedule-content">
                  <span className="schedule-date">{display}</span>
                  <span className="schedule-title">{schedule.title}</span>
                  {cases.length > 1 && schedule.caseName && (
                    <span className="schedule-case">{schedule.caseName}</span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* 권장 사항 */}
      {recommendations.length > 0 && (
        <div className="recommendations">
          <h5>
            <FiCheckSquare /> 권장 사항
          </h5>
          <ul className="recommendation-list">
            {recommendations.slice(0, 4).map((rec, index) => (
              <li
                key={index}
                className="recommendation-item"
                style={{ borderLeftColor: PRIORITY_COLORS[rec.priority] }}
              >
                {rec.priority === 'HIGH' && (
                  <FiAlertTriangle
                    className="priority-icon"
                    style={{ color: PRIORITY_COLORS.HIGH }}
                  />
                )}
                <span>{rec.content}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default UpcomingSchedule;
