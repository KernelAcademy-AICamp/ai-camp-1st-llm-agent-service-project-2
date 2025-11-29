"""
MCP Tools

Phase 4 - Week 12: MCP Tool 정의

도구 목록:
- precedent_tools: 판례 검색/조회
  - search_precedents(query, top_k)
  - get_precedent_details(case_number)
  - search_with_feedback_filtering(query, feedback)

- document_tools: 문서 분석
  - analyze_document(content, doc_type)
  - extract_clauses(content)
  - summarize_document(content)
  - detect_document_type(content)

- case_tools: 사건 분석
  - analyze_case(case_content, case_type)
  - extract_parties(case_content)
  - identify_issues(case_content)
  - search_related_cases(query)
  - assess_case_complexity(case_content)

- analysis_tools: 분석 도구
  - analyze_risks(content, doc_type)
  - calculate_metrics(task, result, ground_truth)
  - compare_documents(doc1, doc2)
  - generate_report(analysis_results)

- llm_tools: LLM 비교 도구
  - execute_on_model(model_name, task, input_data)
  - get_model_metadata(model_name)
  - calculate_llm_metrics(results, task)
  - store_comparison_log(comparison_data)
  - select_best_model(metrics, criteria)

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""

# Precedent Tools
from apps.ai_service.mcp.tools.precedent_tools import (
    search_precedents,
    get_precedent_details,
    search_with_feedback_filtering,
)

# Document Tools
from apps.ai_service.mcp.tools.document_tools import (
    analyze_document,
    extract_clauses,
    summarize_document,
    detect_document_type,
)

# Case Tools
from apps.ai_service.mcp.tools.case_tools import (
    analyze_case,
    extract_parties,
    identify_issues,
    search_related_cases,
    assess_case_complexity,
)

# Analysis Tools
from apps.ai_service.mcp.tools.analysis_tools import (
    analyze_risks,
    calculate_metrics,
    compare_documents,
    generate_report,
    aggregate_statistics,
)

# LLM Tools
from apps.ai_service.mcp.tools.llm_tools import (
    execute_on_model,
    get_model_metadata,
    calculate_llm_metrics,
    store_comparison_log,
    select_best_model,
)

__all__ = [
    # Precedent Tools
    "search_precedents",
    "get_precedent_details",
    "search_with_feedback_filtering",
    # Document Tools
    "analyze_document",
    "extract_clauses",
    "summarize_document",
    "detect_document_type",
    # Case Tools
    "analyze_case",
    "extract_parties",
    "identify_issues",
    "search_related_cases",
    "assess_case_complexity",
    # Analysis Tools
    "analyze_risks",
    "calculate_metrics",
    "compare_documents",
    "generate_report",
    "aggregate_statistics",
    # LLM Tools
    "execute_on_model",
    "get_model_metadata",
    "calculate_llm_metrics",
    "store_comparison_log",
    "select_best_model",
]
