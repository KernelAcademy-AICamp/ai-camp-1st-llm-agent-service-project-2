import React, { useState } from 'react';
import { FiSearch, FiFilter, FiBookOpen, FiBook, FiFileText, FiAlertCircle, FiCheckCircle, FiCopy, FiCheck, FiLoader, FiThumbsUp, FiThumbsDown } from 'react-icons/fi';
import './LegalResearch.css';
import { apiClient } from '../../api/client';
import type { RAGChatResponse } from '../../types';
import PrecedentModal from '../../components/PrecedentModal/PrecedentModal';

const LegalResearch: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [ragResponse, setRagResponse] = useState<RAGChatResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [copied, setCopied] = useState(false);

  // Loading step state
  const [currentStep, setCurrentStep] = useState(0);

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedPrecedent, setSelectedPrecedent] = useState<any>(null);
  const [isLoadingPrecedent, setIsLoadingPrecedent] = useState(false);

  // Feedback states
  const [feedbackState, setFeedbackState] = useState<Record<string, 'like' | 'dislike' | null>>({});

  const handleCopyAnswer = async () => {
    if (ragResponse?.answer) {
      try {
        await navigator.clipboard.writeText(ragResponse.answer);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    }
  };

  const getScoreColor = (score: number) => {
    // RRF 점수는 매우 작은 값 (예: 0.008 ~ 0.015)
    // 상위 결과는 더 높은 RRF 점수를 가짐
    if (score >= 0.010) return 'score-high';
    if (score >= 0.005) return 'score-medium';
    return 'score-low';
  };

  const getScoreLabel = (score: number, rank: number) => {
    // RRF 점수를 사용자 친화적으로 표시
    // 순위 기반 관련도 표시
    if (rank === 1) return '최고 관련';
    if (rank <= 3) return '높은 관련';
    if (rank <= 5) return '관련';
    return '일부 관련';
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setError(null);
    setHasSearched(true);
    setCurrentStep(0);

    try {
      // 단계 1: 문서 검색 시작
      setCurrentStep(1);

      // 단계 2: 2초 후 분석 단계로 전환
      const step2Timer = setTimeout(() => {
        setCurrentStep(2);
      }, 2000);

      // 단계 3: 4초 후 AI 답변 생성 단계로 전환
      const step3Timer = setTimeout(() => {
        setCurrentStep(3);
      }, 4000);

      // RAG Chat API 호출 (Hybrid Search + Constitutional AI)
      const response = await apiClient.chatWithRAG({
        query: searchQuery,
        top_k: topK,
        include_sources: true
      });

      // 타이머 정리
      clearTimeout(step2Timer);
      clearTimeout(step3Timer);

      setRagResponse(response);
    } catch (err) {
      console.error('RAG chat error:', err);
      setError(err instanceof Error ? err.message : 'AI 답변 생성 중 오류가 발생했습니다.');
      setRagResponse(null);
    } finally {
      setIsSearching(false);
      setCurrentStep(0);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'case': return <FiBook />;
      case 'law': return <FiBookOpen />;
      case 'interpretation': return <FiFileText />;
      default: return <FiFileText />;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'case': return '판례';
      case 'law': return '법령';
      case 'interpretation': return '해석례';
      default: return '기타';
    }
  };

  const handlePrecedentClick = async (sourceId: string) => {
    setIsLoadingPrecedent(true);
    setIsModalOpen(true);
    setSelectedPrecedent(null);

    try {
      const detail = await apiClient.getDocumentDetail(sourceId);
      setSelectedPrecedent(detail);
    } catch (err) {
      console.error('Failed to load precedent detail:', err);
      setError(err instanceof Error ? err.message : '판례 상세 정보를 불러오는 데 실패했습니다.');
      setIsModalOpen(false);
    } finally {
      setIsLoadingPrecedent(false);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedPrecedent(null);
  };

  const handleFeedback = async (precedentId: string, feedbackType: 'like' | 'dislike') => {
    try {
      // 세션 ID 생성 (익명 사용자용)
      let sessionId = localStorage.getItem('session_id');
      if (!sessionId) {
        sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        localStorage.setItem('session_id', sessionId);
      }

      await apiClient.submitPrecedentFeedback({
        precedent_id: precedentId,
        query: searchQuery,
        feedback_type: feedbackType,
        is_helpful: feedbackType === 'like',
        session_id: sessionId,
      });

      // 상태 업데이트
      setFeedbackState(prev => ({
        ...prev,
        [precedentId]: feedbackType
      }));

    } catch (err) {
      console.error('Failed to submit feedback:', err);
      setError(err instanceof Error ? err.message : '피드백 제출에 실패했습니다.');
    }
  };

  const handleExampleClick = async (exampleQuery: string) => {
    setSearchQuery(exampleQuery);
    setIsSearching(true);
    setError(null);
    setHasSearched(true);
    setCurrentStep(0);

    try {
      // 단계 1: 문서 검색 시작
      setCurrentStep(1);

      // 단계 2: 2초 후 분석 단계로 전환
      const step2Timer = setTimeout(() => {
        setCurrentStep(2);
      }, 2000);

      // 단계 3: 4초 후 AI 답변 생성 단계로 전환
      const step3Timer = setTimeout(() => {
        setCurrentStep(3);
      }, 4000);

      // RAG Chat API 호출
      const response = await apiClient.chatWithRAG({
        query: exampleQuery,
        top_k: topK,
        include_sources: true
      });

      // 타이머 정리
      clearTimeout(step2Timer);
      clearTimeout(step3Timer);

      setRagResponse(response);
    } catch (err) {
      console.error('RAG chat error:', err);
      setError(err instanceof Error ? err.message : 'AI 답변 생성 중 오류가 발생했습니다.');
      setRagResponse(null);
    } finally {
      setIsSearching(false);
      setCurrentStep(0);
    }
  };

  return (
    <div className="legal-research">
      <div className="research-header">
        <h2>법률 리서치</h2>
        <p>AI 기반 법률 검색으로 빠르고 정확한 답변을 찾아보세요</p>
      </div>

      <form className="search-form" onSubmit={handleSearch}>
        <div className="search-input-wrapper">
          <input
            type="text"
            className="search-input"
            placeholder="예: 위법수집증거의 증거능력 판단 기준은?"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            autoFocus
          />
          <button
            type="submit"
            className="search-button"
            disabled={isSearching}
          >
            {isSearching ? (
              <>
                <FiLoader className="spinner-icon" />
                AI 답변 생성 중...
              </>
            ) : (
              'AI 답변 받기'
            )}
          </button>
        </div>

        <div className="search-filters">
          <span className="filter-label">
            <FiFilter /> 검색 문서 수 (Top-K):
          </span>
          <select
            className="top-k-select"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
          >
            <option value={3}>3개 (빠름)</option>
            <option value={5}>5개 (권장)</option>
            <option value={7}>7개 (상세)</option>
            <option value={10}>10개 (매우 상세)</option>
          </select>
          <span className="search-info">
            388,767개 형사법 문서 | Hybrid Search (Semantic + BM25) | Constitutional AI
          </span>
        </div>
      </form>

      {error && (
        <div className="search-error">
          <FiAlertCircle className="error-icon" />
          <div className="error-content">
            <h4>검색 오류</h4>
            <p>{error}</p>
            <button onClick={() => setError(null)} className="error-dismiss">
              닫기
            </button>
          </div>
        </div>
      )}

      {isSearching && (
        <div className="loading-container">
          <div className="loading-card">
            <div className="loading-header">
              <FiLoader className="loading-spinner" />
              <h3>AI가 답변을 생성하고 있습니다</h3>
            </div>
            <div className="loading-steps">
              <div className={`loading-step ${currentStep >= 1 ? 'active' : ''} ${currentStep > 1 ? 'completed' : ''}`}>
                <div className={`step-indicator ${currentStep === 1 ? 'pulse' : ''}`}>
                  {currentStep > 1 && '✓'}
                </div>
                <span>형사법 문서 검색 중...</span>
              </div>
              <div className={`loading-step ${currentStep >= 2 ? 'active' : ''} ${currentStep > 2 ? 'completed' : ''}`}>
                <div className={`step-indicator ${currentStep === 2 ? 'pulse' : ''}`}>
                  {currentStep > 2 && '✓'}
                </div>
                <span>관련 문서 분석 중...</span>
              </div>
              <div className={`loading-step ${currentStep >= 3 ? 'active' : ''}`}>
                <div className={`step-indicator ${currentStep === 3 ? 'pulse' : ''}`}></div>
                <span>AI 답변 생성 중...</span>
              </div>
            </div>
            <div className="loading-info">
              <p>평균 응답 시간: 5-10초</p>
            </div>
          </div>
        </div>
      )}

      {ragResponse && (
        <div className="rag-response">
          {/* AI Answer Section */}
          <div className="ai-answer-section">
            <div className="answer-header">
              <div className="answer-header-left">
                <h3>AI 답변</h3>
                <div className="answer-meta">
                  <span className="model-badge">{ragResponse.model}</span>
                  {ragResponse.revised && (
                    <span className="revised-badge">
                      <FiCheckCircle /> Self-Critique 검증됨
                    </span>
                  )}
                </div>
              </div>
              <button
                className={`copy-button ${copied ? 'copied' : ''}`}
                onClick={handleCopyAnswer}
                title="답변 복사"
              >
                {copied ? (
                  <>
                    <FiCheck /> 복사됨
                  </>
                ) : (
                  <>
                    <FiCopy /> 복사
                  </>
                )}
              </button>
            </div>
            <div className="answer-content">
              <p className="answer-text">{ragResponse.answer}</p>
            </div>
            <div className="answer-footer">
              <span className="answer-timestamp">
                {new Date(ragResponse.timestamp).toLocaleString('ko-KR')}
              </span>
            </div>
          </div>

          {/* Sources Section */}
          {ragResponse.sources.length > 0 && (
            <div className="sources-section">
              <div className="sources-header">
                <h3>참고 자료 ({ragResponse.sources.length}건)</h3>
                <p className="sources-description">
                  Hybrid Search (Semantic + BM25)로 검색된 관련 문서
                </p>
              </div>
              <div className="sources-list">
                {ragResponse.sources.map((source, index) => {
                  const currentFeedback = feedbackState[source.source];
                  return (
                    <div
                      key={index}
                      className={`source-card ${getScoreColor(source.score)}`}
                    >
                      <div
                        onClick={() => handlePrecedentClick(source.source)}
                        style={{ cursor: 'pointer', flex: 1 }}
                      >
                        <div className="source-header">
                          <div className="source-rank">#{source.rank}</div>
                          <div className="source-title-wrapper">
                            <span className="source-type-icon">{getTypeIcon(source.type)}</span>
                            <h4 className="source-title">{source.title || source.source}</h4>
                          </div>
                          <div className="source-meta">
                            <span className="source-type-label">{getTypeLabel(source.type)}</span>
                            <span className={`source-score ${getScoreColor(source.score)}`}>
                              {getScoreLabel(source.score, source.rank)}
                            </span>
                          </div>
                        </div>
                        <p className="source-snippet">{source.text_snippet}</p>
                        <div className="source-footer">
                          <span className="source-date">{source.date}</span>
                          {source.case_number && (
                            <span className="source-case-number">{source.case_number}</span>
                          )}
                          {source.citation && (
                            <span className="source-citation">{source.citation}</span>
                          )}
                        </div>
                      </div>
                      <div className="source-feedback-buttons">
                        <button
                          className={`feedback-btn ${currentFeedback === 'like' ? 'active liked' : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleFeedback(source.source, 'like');
                          }}
                          title="도움이 되었습니다"
                        >
                          <FiThumbsUp />
                        </button>
                        <button
                          className={`feedback-btn ${currentFeedback === 'dislike' ? 'active disliked' : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleFeedback(source.source, 'dislike');
                          }}
                          title="도움이 되지 않았습니다"
                        >
                          <FiThumbsDown />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {!ragResponse && !isSearching && !hasSearched && (
        <div className="research-placeholder">
          <div className="placeholder-content">
            <FiSearch className="placeholder-icon" />
            <h3>법률 질문을 입력하세요</h3>
            <p>388,767개 형사법 문서에서 AI가 정확한 답변을 찾아드립니다</p>
            <div className="example-queries">
              <h4>예시 질문:</h4>
              <ul>
                <li
                  className="example-query-item"
                  onClick={() => handleExampleClick('절도죄의 구성요건은?')}
                >
                  절도죄의 구성요건은?
                </li>
                <li
                  className="example-query-item"
                  onClick={() => handleExampleClick('위법수집증거 배제 원칙의 예외는?')}
                >
                  위법수집증거 배제 원칙의 예외는?
                </li>
                <li
                  className="example-query-item"
                  onClick={() => handleExampleClick('음주운전 양형 기준')}
                >
                  음주운전 양형 기준
                </li>
                <li
                  className="example-query-item"
                  onClick={() => handleExampleClick('정당방위 성립 요건')}
                >
                  정당방위 성립 요건
                </li>
              </ul>
            </div>
            <div className="tech-info">
              <h4 className="tech-info-title">사용 기술</h4>
              <div className="tech-cards-grid">
                {/* Hybrid Search Card */}
                <div className="tech-card">
                  <div className="tech-card-icon-wrapper">
                    <span className="tech-card-icon">🔍</span>
                  </div>
                  <div className="tech-card-content">
                    <h5 className="tech-card-title">Hybrid Search</h5>
                    <p className="tech-card-description">의미 검색과 키워드 검색을 결합한 하이브리드 방식</p>
                    <ul className="tech-card-list">
                      <li>
                        <strong>Semantic Search</strong>
                        <span className="tech-description">jhgan/ko-sroberta-multitask (768차원 임베딩)</span>
                        <span className="tech-description">코사인 유사도로 의미적 관련성 측정</span>
                      </li>
                      <li>
                        <strong>BM25 (Keyword)</strong>
                        <span className="tech-description">Okapi BM25 (k1=1.5, b=0.75)</span>
                        <span className="tech-description">IDF로 희귀 키워드 가중치 부여</span>
                      </li>
                      <li>
                        <strong>RRF Fusion</strong>
                        <span className="tech-description">Reciprocal Rank Fusion (k=60)</span>
                        <span className="tech-description">순위 기반으로 두 검색 결과 융합</span>
                      </li>
                      <li>
                        <strong>Adaptive Weighting</strong>
                        <span className="tech-description">조항 번호 → BM25 강화 (0.2)</span>
                        <span className="tech-description">의미 질문 → Semantic 강화 (0.7)</span>
                      </li>
                      <li>
                        <strong>실시간 검색</strong>
                        <span className="tech-description">평균 검색 시간 &lt; 1초</span>
                        <span className="tech-description">388,767개 문서 대상 고속 검색</span>
                      </li>
                    </ul>
                    <div className="tech-card-rationale">
                      <div className="rationale-icon">💡</div>
                      <p className="rationale-text">의미 검색만으로는 법률 용어의 정확한 매칭이 어렵고, 키워드 검색만으로는 문맥 이해가 부족합니다. 두 방식을 결합하여 정확도와 재현율을 동시에 향상시킵니다.</p>
                    </div>
                  </div>
                </div>

                {/* Constitutional AI Card */}
                <div className="tech-card">
                  <div className="tech-card-icon-wrapper">
                    <span className="tech-card-icon">🤖</span>
                  </div>
                  <div className="tech-card-content">
                    <h5 className="tech-card-title">Constitutional AI</h5>
                    <p className="tech-card-description">RAG와 6가지 원칙으로 법률 AI의 정확성과 안전성 보장</p>
                    <ul className="tech-card-list">
                      <li>
                        <strong>RAG (검색 증강 생성)</strong>
                        <span className="tech-description">검색된 문서 기반 답변 생성</span>
                        <span className="tech-description">환각(Hallucination) 방지</span>
                      </li>
                      <li>
                        <strong>Constitutional Principles</strong>
                        <span className="tech-description">정확성, 출처 명시, 환각 방지, 전문적 어조</span>
                        <span className="tech-description">면책 조항, 용어 정확성 (6가지 원칙)</span>
                      </li>
                      <li>
                        <strong>Self-Critique</strong>
                        <span className="tech-description">6가지 원칙 검증 후 수정</span>
                        <span className="tech-description">답변 품질 자동 개선</span>
                      </li>
                      <li>
                        <strong>Few-Shot Learning</strong>
                        <span className="tech-description">3-Shot: 예시 기반 패턴 학습</span>
                        <span className="tech-description">법률 답변 스타일 일관성 유지</span>
                      </li>
                      <li>
                        <strong>Prompt Engineering</strong>
                        <span className="tech-description">고급 프롬프트 최적화 기법</span>
                        <span className="tech-description">Chain-of-Thought 추론</span>
                      </li>
                    </ul>
                    <div className="tech-card-rationale">
                      <div className="rationale-icon">💡</div>
                      <p className="rationale-text">RAG로 검색된 실제 법률 문서를 기반으로 답변을 생성하여 환각을 방지합니다. Constitutional AI 원칙으로 법률 AI의 정확성, 신뢰성, 검증 가능성을 보장합니다.</p>
                    </div>
                  </div>
                </div>

                {/* Data & Model Card */}
                <div className="tech-card">
                  <div className="tech-card-icon-wrapper">
                    <span className="tech-card-icon">📊</span>
                  </div>
                  <div className="tech-card-content">
                    <h5 className="tech-card-title">Data & Model</h5>
                    <p className="tech-card-description">대규모 형사법 데이터와 최신 AI 모델</p>
                    <div className="tech-card-stat">
                      <div className="stat-number">388,767</div>
                      <div className="stat-label">형사법 문서 (판례, 법령, 해석례)</div>
                    </div>
                    <ul className="tech-card-list">
                      <li>
                        <strong>LLM</strong>
                        <span className="tech-description">GPT-4 Turbo (gpt-4-turbo-preview)</span>
                      </li>
                      <li>
                        <strong>Vector DB</strong>
                        <span className="tech-description">ChromaDB (HNSW, 3.9GB)</span>
                      </li>
                      <li>
                        <strong>BM25 Index</strong>
                        <span className="tech-description">388,767 documents indexed</span>
                      </li>
                      <li>
                        <strong>Embedding Model</strong>
                        <span className="tech-description">KR-SBERT (768-dim)</span>
                      </li>
                      <li>
                        <strong>데이터 출처</strong>
                        <span className="tech-description">법제처 Open API, 대법원 종합법률정보</span>
                      </li>
                    </ul>
                    <div className="tech-card-rationale">
                      <div className="rationale-icon">💡</div>
                      <p className="rationale-text">형사법 전문 AI를 위해 판례, 법령, 해석례 등 38만여 건의 실제 법률 문서를 수집했습니다. GPT-4 Turbo와 한국어 특화 임베딩 모델로 최고의 성능을 보장합니다.</p>
                    </div>
                  </div>
                </div>

                {/* User Feedback Card */}
                <div className="tech-card">
                  <div className="tech-card-icon-wrapper">
                    <span className="tech-card-icon">👍</span>
                  </div>
                  <div className="tech-card-content">
                    <h5 className="tech-card-title">사용자 피드백</h5>
                    <p className="tech-card-description">검색 품질 향상을 위한 피드백 시스템</p>
                    <ul className="tech-card-list">
                      <li>
                        <strong>피드백 수집</strong>
                        <span className="tech-description">좋아요/싫어요 양방향 평가</span>
                        <span className="tech-description">검색 쿼리와 판례 ID 매핑 저장</span>
                      </li>
                      <li>
                        <strong>판례 상세 보기</strong>
                        <span className="tech-description">Modal 기반 전문 내용 표시</span>
                        <span className="tech-description">사건번호, 선고일, 판결요지 구조화</span>
                      </li>
                      <li>
                        <strong>세션 추적</strong>
                        <span className="tech-description">LocalStorage 기반 익명 세션 ID</span>
                        <span className="tech-description">검색 히스토리 및 클릭 패턴 분석</span>
                      </li>
                      <li>
                        <strong>데이터베이스 저장</strong>
                        <span className="tech-description">PostgreSQL 기반 피드백 영구 저장</span>
                        <span className="tech-description">향후 Ranking 모델 학습 데이터 활용</span>
                      </li>
                    </ul>
                    <div className="tech-card-rationale">
                      <div className="rationale-icon">💡</div>
                      <p className="rationale-text">사용자 피드백을 수집하여 검색 결과의 정확도를 지속적으로 개선합니다. 실제 사용 패턴을 분석해 법률 전문가의 요구에 맞춰 진화하는 시스템입니다.</p>
                    </div>
                  </div>
                </div>

                {/* Automation Card */}
                <div className="tech-card">
                  <div className="tech-card-icon-wrapper">
                    <span className="tech-card-icon">🔄</span>
                  </div>
                  <div className="tech-card-content">
                    <h5 className="tech-card-title">자동화 시스템</h5>
                    <p className="tech-card-description">최신 판례 자동 수집 및 업데이트</p>
                    <ul className="tech-card-list">
                      <li>
                        <strong>일일 판례 크롤링</strong>
                        <span className="tech-description">매일 00:00 최신 형사 판례 자동 수집</span>
                        <span className="tech-description">Playwright로 대법원 웹사이트 동적 크롤링</span>
                        <span className="tech-description">최신 판결 10건 자동 인덱싱</span>
                      </li>
                      <li>
                        <strong>주간 맞춤 크롤링</strong>
                        <span className="tech-description">일요일 00:00 선호도 기반 수집</span>
                        <span className="tech-description">사용자 피드백 반영 판례 선별</span>
                      </li>
                      <li>
                        <strong>APScheduler</strong>
                        <span className="tech-description">Python 기반 스케줄링 시스템</span>
                        <span className="tech-description">Cron 표현식으로 정확한 시간 관리</span>
                      </li>
                      <li>
                        <strong>Law.go.kr API</strong>
                        <span className="tech-description">법제처 공식 API 연동</span>
                        <span className="tech-description">XML 파싱 및 자동 인덱싱</span>
                      </li>
                    </ul>
                    <div className="tech-card-rationale">
                      <div className="rationale-icon">💡</div>
                      <p className="rationale-text">최신 판례를 자동으로 수집하여 데이터베이스를 실시간으로 업데이트합니다. 법률 환경의 변화를 즉시 반영해 항상 최신 정보를 제공합니다.</p>
                    </div>
                  </div>
                </div>

                {/* Document Generation Card */}
                <div className="tech-card">
                  <div className="tech-card-icon-wrapper">
                    <span className="tech-card-icon">📝</span>
                  </div>
                  <div className="tech-card-content">
                    <h5 className="tech-card-title">문서 자동 생성</h5>
                    <p className="tech-card-description">AI 기반 법률 문서 자동 작성 시스템</p>
                    <ul className="tech-card-list">
                      <li>
                        <strong>8가지 시나리오 자동 감지</strong>
                        <span className="tech-description">키워드 매칭 기반 점수 계산 (0.0~1.0)</span>
                        <span className="tech-description">문서 타입, 당사자, 법률 용어 분석</span>
                        <span className="tech-description">Confidence Score 기반 추천 시스템</span>
                      </li>
                      <li>
                        <strong>6가지 템플릿 지원</strong>
                        <span className="tech-description">소장, 답변서, 고소장, 변론요지서, 내용증명, 손해배상청구서</span>
                        <span className="tech-description">변수 자동 치환 ({"{{placeholder}}"} → 실제 값)</span>
                      </li>
                      <li>
                        <strong>AI 사건 분석</strong>
                        <span className="tech-description">GPT 기반 문서 요약 및 쟁점 추출</span>
                        <span className="tech-description">당사자/날짜/증거 자동 인식</span>
                        <span className="tech-description">관련 판례 RAG 검색 및 추천</span>
                      </li>
                      <li>
                        <strong>스마트 매핑 시스템</strong>
                        <span className="tech-description">업로드 문서에서 당사자 정보 자동 추출</span>
                        <span className="tech-description">금액/날짜 자동 포맷팅 (천단위 콤마)</span>
                        <span className="tech-description">Unfilled placeholder 검증 및 경고</span>
                      </li>
                    </ul>
                    <div className="tech-card-rationale">
                      <div className="rationale-icon">💡</div>
                      <p className="rationale-text">변호사의 반복 작업을 AI로 자동화하여 시간을 절약합니다. 템플릿 기반 생성으로 일관성을 유지하고, RAG로 판례 기반 맞춤형 문서를 작성합니다.</p>
                    </div>
                  </div>
                </div>

                {/* Document-Aware Chunking Card */}
                <div className="tech-card">
                  <div className="tech-card-icon-wrapper">
                    <span className="tech-card-icon">📑</span>
                  </div>
                  <div className="tech-card-content">
                    <h5 className="tech-card-title">도메인 특화 청킹 전략</h5>
                    <p className="tech-card-description">문서 타입별로 최적화된 청킹 전략 적용</p>
                    <ul className="tech-card-list">
                      <li>
                        <strong>판례 문서 (37,000건)</strong>
                        <span className="tech-description">문장 기반 적응형 청킹 (Sentence-Based)</span>
                        <span className="tech-description">500자 고정 (~250 토큰)</span>
                        <span className="tech-description">마침표·줄바꿈 기준, 오버랩 없음</span>
                        <span className="tech-description">순차적 서술 구조 유지</span>
                      </li>
                      <li>
                        <strong>법령 문서 (3,000건)</strong>
                        <span className="tech-description">조문 단위 의미론적 청킹 (Article-Based)</span>
                        <span className="tech-description">가변 길이 (100~1500자, 조문별)</span>
                        <span className="tech-description">제N조 경계 기준, 조문 완전성 보장</span>
                        <span className="tech-description">법률 구조 준수</span>
                      </li>
                      <li>
                        <strong>범용 처리 (Langchain)</strong>
                        <span className="tech-description">계층적 재귀 분할 (RecursiveCharacterTextSplitter)</span>
                        <span className="tech-description">500자 목표, 50자 오버랩 (10%)</span>
                        <span className="tech-description">단락 → 문장 → 구 → 단어 순 분리</span>
                        <span className="tech-description">자연스러운 경계 우선, 문맥 연결</span>
                      </li>
                      <li>
                        <strong>기술 스택</strong>
                        <span className="tech-description">커스텀 파서 (판례/법령 특화 처리)</span>
                        <span className="tech-description">Langchain RecursiveCharacterTextSplitter</span>
                        <span className="tech-description">정규식 메타데이터 자동 추출</span>
                        <span className="tech-description">총 청크 수: 388,767개 (ChromaDB)</span>
                      </li>
                    </ul>
                    <div className="tech-card-rationale">
                      <div className="rationale-icon">💡</div>
                      <p className="rationale-text">판례는 순차적 서술이므로 문장 단위로 분할하고, 법령은 조문별 독립성이 중요하므로 조문 단위로 처리합니다. 각 문서 도메인의 특성을 존중하여 검색 정밀도를 최적화했습니다.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {!ragResponse && !isSearching && hasSearched && !error && (
        <div className="research-placeholder">
          <div className="placeholder-content">
            <FiAlertCircle className="placeholder-icon" />
            <h3>답변을 생성할 수 없습니다</h3>
            <p>"{searchQuery}"에 대한 관련 문서를 찾을 수 없습니다.</p>
            <div className="example-queries">
              <h4>다음을 시도해보세요:</h4>
              <ul>
                <li>다른 키워드로 질문해보세요</li>
                <li>질문을 더 구체적으로 입력해보세요</li>
                <li>법률 용어를 사용해보세요</li>
                <li>Top-K 값을 늘려보세요 (현재: {topK})</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Precedent Modal */}
      <PrecedentModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        precedentData={selectedPrecedent}
        isLoading={isLoadingPrecedent}
      />
    </div>
  );
};

export default LegalResearch;