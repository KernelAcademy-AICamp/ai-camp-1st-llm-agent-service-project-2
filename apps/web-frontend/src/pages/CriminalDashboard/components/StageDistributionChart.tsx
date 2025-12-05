import React from 'react';
import { CriminalCase, CriminalStage, CRIMINAL_STAGE_LABELS } from '../../../types';

interface StageDistributionChartProps {
  cases: CriminalCase[];
}

// 단계별 색상
const STAGE_COLORS: Record<CriminalStage, string> = {
  COMPLAINT: '#f59e0b',
  INVESTIGATION: '#3b82f6',
  PROSECUTION: '#8b5cf6',
  TRIAL: '#ec4899',
  JUDGMENT: '#10b981',
  CLOSED: '#6b7280',
};

const StageDistributionChart: React.FC<StageDistributionChartProps> = ({ cases }) => {
  // 단계별 사건 수 계산
  const stageCounts = cases.reduce((acc, c) => {
    acc[c.stage] = (acc[c.stage] || 0) + 1;
    return acc;
  }, {} as Record<CriminalStage, number>);

  const total = cases.length;

  // 데이터 배열로 변환
  const data = Object.entries(stageCounts)
    .map(([stage, count]) => ({
      stage: stage as CriminalStage,
      count,
      percentage: total > 0 ? Math.round((count / total) * 100) : 0,
      color: STAGE_COLORS[stage as CriminalStage],
      label: CRIMINAL_STAGE_LABELS[stage as CriminalStage],
    }))
    .sort((a, b) => b.count - a.count);

  // SVG 도넛 차트 계산
  const size = 160;
  const strokeWidth = 24;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let currentOffset = 0;
  const segments = data.map((item) => {
    const segmentLength = (item.count / total) * circumference;
    const segment = {
      ...item,
      offset: currentOffset,
      length: segmentLength,
    };
    currentOffset += segmentLength;
    return segment;
  });

  if (total === 0) {
    return (
      <div className="chart-card stage-distribution-chart">
        <h4 className="chart-title">단계별 사건 분포</h4>
        <div className="empty-chart">
          <p>등록된 사건이 없습니다</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chart-card stage-distribution-chart">
      <h4 className="chart-title">단계별 사건 분포</h4>

      <div className="chart-content">
        {/* 도넛 차트 */}
        <div className="donut-chart-container">
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            {/* 배경 원 */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="#e5e7eb"
              strokeWidth={strokeWidth}
            />

            {/* 세그먼트 */}
            {segments.map((segment, index) => (
              <circle
                key={segment.stage}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={segment.color}
                strokeWidth={strokeWidth}
                strokeDasharray={`${segment.length} ${circumference - segment.length}`}
                strokeDashoffset={-segment.offset}
                transform={`rotate(-90 ${size / 2} ${size / 2})`}
                style={{ transition: 'stroke-dasharray 0.3s ease' }}
              />
            ))}
          </svg>

          {/* 중앙 텍스트 */}
          <div className="donut-center">
            <span className="donut-total">{total}</span>
            <span className="donut-label">전체</span>
          </div>
        </div>

        {/* 범례 */}
        <div className="chart-legend">
          {data.map((item) => (
            <div key={item.stage} className="legend-item">
              <span
                className="legend-color"
                style={{ backgroundColor: item.color }}
              />
              <span className="legend-label">{item.label}</span>
              <span className="legend-value">{item.count}건</span>
              <span className="legend-percent">({item.percentage}%)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default StageDistributionChart;
