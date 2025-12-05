import React from 'react';
import { FiPaperclip, FiBookOpen, FiArrowRight, FiPhone } from 'react-icons/fi';
import { CriminalCaseAnalysis } from '../../../types';
import './SimpleCards.css';

interface NextStepsCardProps {
  analysis: CriminalCaseAnalysis;
}

interface NextStep {
  text: string;
  priority: 'high' | 'medium' | 'low';
  category: 'evidence' | 'legal' | 'action';
}

const NextStepsCard: React.FC<NextStepsCardProps> = ({ analysis }) => {
  // 분석 결과 기반으로 다음 단계 생성
  const generateNextSteps = (): NextStep[] => {
    const steps: NextStep[] = [];
    const crimeType = analysis.crime_type || '';
    const elements = analysis.crime_elements;

    // 1. 구성요건 미충족 시 증거 수집 권장
    if (elements) {
      const allElements = [
        ...(elements.objective || []),
        ...(elements.subjective || []),
      ];
      const unfulfilledElements = allElements.filter(e => !e.fulfilled);

      if (unfulfilledElements.length > 0) {
        steps.push({
          text: '추가 증거 수집하기 (대화 기록, 사진, 목격자 진술 등)',
          priority: 'high',
          category: 'evidence',
        });
      }
    }

    // 2. 범죄 유형별 특화 단계
    if (crimeType.includes('사기') || crimeType.includes('횡령')) {
      steps.push({
        text: '피해 금액 증빙 자료 정리하기 (계좌이체 내역, 영수증)',
        priority: 'high',
        category: 'evidence',
      });
    }

    if (crimeType.includes('폭행') || crimeType.includes('상해')) {
      steps.push({
        text: '병원에서 진단서 발급받기',
        priority: 'high',
        category: 'evidence',
      });
      steps.push({
        text: 'CCTV 영상 확보 요청하기',
        priority: 'medium',
        category: 'evidence',
      });
    }

    if (crimeType.includes('협박') || crimeType.includes('스토킹')) {
      steps.push({
        text: '협박 메시지/전화 녹취록 저장하기',
        priority: 'high',
        category: 'evidence',
      });
    }

    if (crimeType.includes('명예훼손') || crimeType.includes('모욕')) {
      steps.push({
        text: '게시글/댓글 스크린샷 캡처하기 (URL, 날짜 포함)',
        priority: 'high',
        category: 'evidence',
      });
    }

    // 3. 공통 단계
    steps.push({
      text: '가까운 경찰서 방문하여 고소장 접수하기',
      priority: 'high',
      category: 'action',
    });

    steps.push({
      text: '고소장 접수 시 사건접수번호 받아두기',
      priority: 'medium',
      category: 'action',
    });

    // 4. 선택적 단계
    const hasLowPossibility =
      elements &&
      [...(elements.objective || []), ...(elements.subjective || [])].filter(
        e => e.fulfilled
      ).length <
        [...(elements.objective || []), ...(elements.subjective || [])].length *
          0.5;

    if (hasLowPossibility) {
      steps.push({
        text: '변호사 무료 상담 받아보기 (대한법률구조공단: 132)',
        priority: 'medium',
        category: 'legal',
      });
    }

    steps.push({
      text: '수사 진행 상황 주기적으로 확인하기',
      priority: 'low',
      category: 'action',
    });

    return steps;
  };

  const steps = generateNextSteps();

  const priorityConfig = {
    high: { label: '중요', color: '#ef4444', bgColor: '#fef2f2' },
    medium: { label: '권장', color: '#f59e0b', bgColor: '#fffbeb' },
    low: { label: '선택', color: '#6b7280', bgColor: '#f3f4f6' },
  };

  const categoryIcons: Record<string, React.ReactNode> = {
    evidence: <FiPaperclip className="step-category-icon" />,
    legal: <FiBookOpen className="step-category-icon" />,
    action: <FiArrowRight className="step-category-icon" />,
  };

  return (
    <div className="simple-card next-steps-card">
      <div className="card-header">
        <h4>다음에 할 일</h4>
        <span className="card-subtitle">순서대로 진행하세요</span>
      </div>

      <div className="steps-content">
        <ol className="steps-list">
          {steps.map((step, idx) => (
            <li key={idx} className={`step-item priority-${step.priority}`}>
              <div className="step-number">
                <span>{idx + 1}</span>
              </div>
              <div className="step-details">
                <div className="step-text">
                  <span className="category-icon">{categoryIcons[step.category]}</span>
                  {step.text}
                </div>
                <span
                  className="priority-badge"
                  style={{
                    backgroundColor: priorityConfig[step.priority].bgColor,
                    color: priorityConfig[step.priority].color,
                  }}
                >
                  {priorityConfig[step.priority].label}
                </span>
              </div>
            </li>
          ))}
        </ol>

        <div className="helpful-contacts">
          <h5>도움받을 수 있는 곳</h5>
          <ul>
            <li>
              <FiPhone className="contact-icon" />
              <span>대한법률구조공단: <strong>132</strong></span>
            </li>
            <li>
              <FiPhone className="contact-icon" />
              <span>경찰 민원: <strong>182</strong></span>
            </li>
            <li>
              <FiPhone className="contact-icon" />
              <span>검찰 민원: <strong>1301</strong></span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default NextStepsCard;
