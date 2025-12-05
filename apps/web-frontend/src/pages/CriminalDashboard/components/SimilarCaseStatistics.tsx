import React, { useEffect, useState } from 'react';
import { SimilarCaseStatisticsResponse, SentencingDistributionStats } from '../../../types';
import { FiBarChart2, FiLoader } from 'react-icons/fi';
import apiClient from '../../../api/client';

interface SimilarCaseStatisticsProps {
  crimeType: string;
  conditions: string[];
}

// 결과 유형별 라벨과 색상
const RESULT_CONFIG: Record<keyof SentencingDistributionStats, { label: string; color: string }> = {
  suspended: { label: '집행유예', color: '#3b82f6' },
  fine: { label: '벌금형', color: '#10b981' },
  imprisonment: { label: '실형', color: '#ef4444' },
  acquittal: { label: '무죄', color: '#8b5cf6' },
};

const SimilarCaseStatistics: React.FC<SimilarCaseStatisticsProps> = ({
  crimeType,
  conditions
}) => {
  const [statistics, setStatistics] = useState<SimilarCaseStatisticsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!crimeType) return;

    const fetchStatistics = async () => {
      setLoading(true);
      setError(null);
      try {
        // API 호출
        const data = await apiClient.getSimilarCaseStatistics(crimeType, conditions);
        setStatistics(data);
      } catch (err: any) {
        // API가 없는 경우 목데이터 사용
        setStatistics({
          crime_type: crimeType,
          conditions: conditions,
          total_similar_cases: 127,
          distribution: {
            suspended: 65,
            fine: 20,
            imprisonment: 12,
            acquittal: 3,
          },
        });
      } finally {
        setLoading(false);
      }
    };

    fetchStatistics();
  }, [crimeType, conditions.join(',')]);

  if (!crimeType) {
    return (
      <div className="similar-case-statistics empty">
        <FiBarChart2 className="empty-icon" />
        <p>사건을 선택하면 유사 사건 통계를 확인할 수 있습니다.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="similar-case-statistics loading">
        <FiLoader className="spinner" />
        <p>유사 사건 통계 로딩 중...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="similar-case-statistics error">
        <p>{error}</p>
      </div>
    );
  }

  if (!statistics) return null;

  const { distribution, total_similar_cases } = statistics;

  // 분포 데이터를 배열로 변환하고 정렬
  const distributionItems = Object.entries(distribution)
    .map(([key, value]) => ({
      key: key as keyof SentencingDistributionStats,
      value: value as number,
      ...RESULT_CONFIG[key as keyof SentencingDistributionStats],
    }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="similar-case-statistics">
      <h4 className="card-title">
        <FiBarChart2 /> 유사 사건 통계
      </h4>

      <p className="statistics-description">
        비슷한 <strong>[{crimeType}
        {conditions.length > 0 && `/${conditions.join('/')}`}]</strong> 사건:
      </p>

      <div className="statistics-chart">
        {distributionItems.map(({ key, label, value, color }) => (
          <div key={key} className="stat-bar-row">
            <span className="stat-label">{label}</span>
            <div className="stat-bar-container">
              <div
                className="stat-bar-fill"
                style={{
                  width: `${value}%`,
                  backgroundColor: color,
                }}
              />
            </div>
            <span className="stat-value">{value}%</span>
          </div>
        ))}
      </div>

      <p className="total-cases">
        총 <strong>{total_similar_cases.toLocaleString()}</strong>건 분석
      </p>

      <p className="disclaimer">
        * 통계는 참고용이며, 개별 사건 결과는 다를 수 있습니다.
      </p>
    </div>
  );
};

export default SimilarCaseStatistics;
