import React, { useState } from 'react';
import { FiSearch, FiFilter, FiBookOpen, FiBook, FiFileText, FiAlertCircle, FiCheckCircle, FiCopy, FiCheck, FiLoader } from 'react-icons/fi';
import './LegalResearch.css';
import { apiClient } from '../../api/client';
import type { RAGChatResponse } from '../../types';

const LegalResearch: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [ragResponse, setRagResponse] = useState<RAGChatResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [copied, setCopied] = useState(false);

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

    try {
      // RAG Chat API 호출 (Hybrid Search + Constitutional AI)
      const response = await apiClient.chatWithRAG({
        query: searchQuery,
        top_k: topK,
        include_sources: true
      });

      setRagResponse(response);
    } catch (err) {
      console.error('RAG chat error:', err);
      setError(err instanceof Error ? err.message : 'AI 답변 생성 중 오류가 발생했습니다.');
      setRagResponse(null);
    } finally {
      setIsSearching(false);
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
              <div className="loading-step active">
                <div className="step-indicator pulse"></div>
                <span>형사법 문서 검색 중...</span>
              </div>
              <div className="loading-step">
                <div className="step-indicator"></div>
                <span>관련 문서 분석 중...</span>
              </div>
              <div className="loading-step">
                <div className="step-indicator"></div>
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
                {ragResponse.sources.map((source, index) => (
                  <div key={index} className={`source-card ${getScoreColor(source.score)}`}>
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
                ))}
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
                <li>"절도죄의 구성요건은?"</li>
                <li>"위법수집증거 배제 원칙의 예외는?"</li>
                <li>"음주운전 양형 기준"</li>
                <li>"정당방위 성립 요건"</li>
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
                      </li>
                      <li>
                        <strong>BM25 (Keyword)</strong>
                        <span className="tech-description">Okapi BM25 (k1=1.5, b=0.75)</span>
                      </li>
                      <li>
                        <strong>RRF Fusion</strong>
                        <span className="tech-description">Reciprocal Rank Fusion (k=60)</span>
                      </li>
                      <li>
                        <strong>Adaptive Weighting</strong>
                        <span className="tech-description">쿼리 유형별 가중치 자동 조정</span>
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
                    <p className="tech-card-description">6가지 원칙으로 법률 AI의 정확성과 안전성 보장</p>
                    <ul className="tech-card-list">
                      <li>
                        <strong>정확성</strong>
                        <span className="tech-description">검색 문서 기반, 추측 금지</span>
                      </li>
                      <li>
                        <strong>출처 명시</strong>
                        <span className="tech-description">모든 주장에 출처 표시</span>
                      </li>
                      <li>
                        <strong>환각 방지</strong>
                        <span className="tech-description">모르면 "정보 부족" 명시</span>
                      </li>
                      <li>
                        <strong>전문적 어조</strong>
                        <span className="tech-description">객관적, 법률적 표현</span>
                      </li>
                      <li>
                        <strong>면책 조항</strong>
                        <span className="tech-description">법률 정보 제공 (자문 아님)</span>
                      </li>
                      <li>
                        <strong>용어 정확성</strong>
                        <span className="tech-description">정확한 법률 용어</span>
                      </li>
                      <li>
                        <strong>Self-Critique</strong>
                        <span className="tech-description">6가지 원칙 검증 후 수정</span>
                      </li>
                      <li>
                        <strong>3-Shot Learning</strong>
                        <span className="tech-description">예시 기반 패턴 학습</span>
                      </li>
                    </ul>
                    <div className="tech-card-rationale">
                      <div className="rationale-icon">💡</div>
                      <p className="rationale-text">법률 분야는 정확성과 신뢰성이 생명입니다. 일반 LLM의 환각(hallucination) 문제를 해결하고, 모든 답변에 출처를 명시하여 사용자가 검증 가능하도록 했습니다.</p>
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
                        <span className="tech-description">GPT-4 Turbo (Preview)</span>
                      </li>
                      <li>
                        <strong>Vector DB</strong>
                        <span className="tech-description">ChromaDB (Persistent, 3.9GB)</span>
                      </li>
                      <li>
                        <strong>Embedding Model</strong>
                        <span className="tech-description">KR-SBERT (768-dim)</span>
                      </li>
                    </ul>
                    <div className="tech-card-rationale">
                      <div className="rationale-icon">💡</div>
                      <p className="rationale-text">형사법 전문 AI를 위해 판례, 법령, 해석례 등 38만여 건의 실제 법률 문서를 수집했습니다. GPT-4 Turbo와 한국어 특화 임베딩 모델로 최고의 성능을 보장합니다.</p>
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
    </div>
  );
};

export default LegalResearch;