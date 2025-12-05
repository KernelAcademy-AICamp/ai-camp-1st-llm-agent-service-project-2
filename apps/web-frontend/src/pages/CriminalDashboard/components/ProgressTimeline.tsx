import React from 'react';
import { CriminalCase, CriminalStage, CRIMINAL_STAGE_LABELS } from '../../../types';

interface ProgressTimelineProps {
  cases: CriminalCase[];
}

// 형사 절차 단계 순서
const STAGE_ORDER: CriminalStage[] = [
  'COMPLAINT',
  'INVESTIGATION',
  'PROSECUTION',
  'TRIAL',
  'JUDGMENT',
];

// 단계별 색상
const STAGE_COLORS: Record<CriminalStage, string> = {
  COMPLAINT: '#f59e0b',
  INVESTIGATION: '#3b82f6',
  PROSECUTION: '#8b5cf6',
  TRIAL: '#ec4899',
  JUDGMENT: '#10b981',
  CLOSED: '#6b7280',
};

const ProgressTimeline: React.FC<ProgressTimelineProps> = ({ cases }) => {
  // 활성 사건만 필터 (CLOSED 제외)
  const activeCases = cases.filter(c => c.stage !== 'CLOSED');

  // 단계별 사건 수 계산
  const casesByStage = STAGE_ORDER.reduce((acc, stage) => {
    acc[stage] = activeCases.filter(c => c.stage === stage).length;
    return acc;
  }, {} as Record<CriminalStage, number>);

  // 현재 단계 (가장 최근 사건 기준)
  const currentStage = activeCases.length > 0
    ? activeCases[0].stage
    : null;

  const currentStageIndex = currentStage
    ? STAGE_ORDER.indexOf(currentStage)
    : -1;

  // 사건 1개인 경우와 여러 개인 경우 표시 방식 분리
  const singleCaseMode = activeCases.length === 1;

  return (
    <div className="progress-timeline">
      <h3 className="timeline-title">진행 상황 타임라인</h3>

      <div className="timeline-container">
        <div className="timeline-track">
          {STAGE_ORDER.map((stage, index) => {
            // 여러 사건이 있을 때는 완료 표시를 하지 않음 (각 사건이 다른 단계에 있을 수 있음)
            const isCompleted = singleCaseMode && currentStageIndex > index;
            const isCurrent = singleCaseMode ? currentStageIndex === index : casesByStage[stage] > 0;
            const caseCount = casesByStage[stage];

            return (
              <React.Fragment key={stage}>
                {/* 연결선 */}
                {index > 0 && (
                  <div
                    className={`timeline-connector ${isCompleted || isCurrent ? 'active' : ''}`}
                  />
                )}

                {/* 단계 노드 */}
                <div className="timeline-node-wrapper">
                  <div
                    className={`timeline-node ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''}`}
                    style={{
                      borderColor: isCurrent || isCompleted ? STAGE_COLORS[stage] : '#d1d5db',
                      backgroundColor: isCompleted ? STAGE_COLORS[stage] : isCurrent ? `${STAGE_COLORS[stage]}20` : 'white',
                    }}
                  >
                    {isCompleted ? (
                      <svg className="check-icon" viewBox="0 0 24 24" fill="white">
                        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
                      </svg>
                    ) : (
                      !singleCaseMode && caseCount > 0 && (
                        <span className="case-count">{caseCount}</span>
                      )
                    )}
                  </div>

                  <div className="timeline-label">
                    <span className="stage-name">{CRIMINAL_STAGE_LABELS[stage]}</span>
                    {!singleCaseMode && caseCount > 0 && (
                      <span className="stage-count">{caseCount}건</span>
                    )}
                  </div>

                  {singleCaseMode && isCurrent && (
                    <div className="current-indicator">
                      <span className="pulse"></span>
                      현재 단계
                    </div>
                  )}
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* 사건 현황 요약 */}
      <div className="timeline-summary">
        {activeCases.length === 0 ? (
          <p className="no-cases">진행 중인 사건이 없습니다.</p>
        ) : singleCaseMode ? (
          <p className="single-case-info">
            내 사건: <strong>{currentStage ? CRIMINAL_STAGE_LABELS[currentStage] : '미정'}</strong> 단계
          </p>
        ) : (
          <p className="multi-case-info">
            총 <strong>{activeCases.length}건</strong>의 형사 사건 진행 중
          </p>
        )}
      </div>
    </div>
  );
};

export default ProgressTimeline;
