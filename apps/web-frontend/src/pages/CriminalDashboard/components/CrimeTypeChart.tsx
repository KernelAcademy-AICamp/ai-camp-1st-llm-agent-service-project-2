import React from 'react';
import { CriminalCase, CrimeTypeCount } from '../../../types';
import { FiPieChart } from 'react-icons/fi';

interface CrimeTypeChartProps {
  cases: CriminalCase[];
}

// 범죄 유형별 색상
const CRIME_TYPE_COLORS: Record<string, string> = {
  '절도': '#3b82f6',
  '사기': '#ef4444',
  '폭행': '#f59e0b',
  '상해': '#f97316',
  '횡령': '#8b5cf6',
  '배임': '#a855f7',
  '마약': '#10b981',
  '음주운전': '#06b6d4',
  '성범죄': '#ec4899',
  '살인': '#dc2626',
  'default': '#6b7280',
};

const CrimeTypeChart: React.FC<CrimeTypeChartProps> = ({ cases }) => {
  // 범죄 유형별 사건 수 집계
  const crimeTypeCounts: CrimeTypeCount[] = cases.reduce((acc, c) => {
    const type = c.crime_type || '기타';
    const existing = acc.find(item => item.crime_type === type);
    if (existing) {
      existing.count++;
    } else {
      acc.push({ crime_type: type, count: 1 });
    }
    return acc;
  }, [] as CrimeTypeCount[]);

  // 건수 순으로 정렬
  const sortedCounts = crimeTypeCounts.sort((a, b) => b.count - a.count);

  // 최대값 (바 차트 스케일링용)
  const maxCount = Math.max(...sortedCounts.map(c => c.count), 1);

  // 색상 가져오기
  const getColor = (crimeType: string): string => {
    return CRIME_TYPE_COLORS[crimeType] || CRIME_TYPE_COLORS['default'];
  };

  if (cases.length === 0) {
    return (
      <div className="chart-card crime-type-chart">
        <h4 className="chart-title">
          <FiPieChart /> 범죄 유형별 분포
        </h4>
        <div className="empty-chart">
          <p>등록된 사건이 없습니다</p>
        </div>
      </div>
    );
  }

  return (
    <div className="crime-type-chart">
      <h4 className="card-title">
        <FiPieChart /> 범죄 유형별 분포
      </h4>

      <div className="chart-container">
        {sortedCounts.map(({ crime_type, count }) => {
          const percentage = Math.round((count / cases.length) * 100);
          const barWidth = (count / maxCount) * 100;

          return (
            <div key={crime_type} className="chart-row">
              <span className="chart-label">{crime_type}</span>
              <div className="chart-bar-container">
                <div
                  className="chart-bar-fill"
                  style={{
                    width: `${barWidth}%`,
                    backgroundColor: getColor(crime_type),
                  }}
                />
              </div>
              <span className="chart-value">{count}건 ({percentage}%)</span>
            </div>
          );
        })}
      </div>

      <p className="chart-total">
        총 <strong>{cases.length}</strong>건
      </p>
    </div>
  );
};

export default CrimeTypeChart;
