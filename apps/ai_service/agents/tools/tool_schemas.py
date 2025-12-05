"""
Tool Schemas - LLM Tool Use를 위한 JSON Schema 정의

LLM의 Native Tool Use (Function Calling) 기능을 활용하기 위한
JSON Schema 형식의 도구 정의입니다.

OpenAI와 Anthropic 양쪽 형식을 지원합니다.
"""

from typing import Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Hub에서 사용할 도구 정의 (JSON Schema 형식)
# =============================================================================

TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # 검색 도구
    # =========================================================================
    "search_legal": {
        "name": "search_legal",
        "description": "법률 정보를 검색합니다. 법령, 판례, 법률 개념, 조문 등을 찾을 때 사용합니다. 법률 관련 질문에 답변하기 위한 기본 도구입니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색할 법률 관련 질문 또는 키워드"
                },
                "top_k": {
                    "type": "integer",
                    "description": "반환할 검색 결과 수",
                    "default": 5
                }
            },
            "required": ["query"]
        },
        "workflow_name": "rag_workflow",
        "category": "search"
    },

    "search_precedents": {
        "name": "search_precedents",
        "description": "관련 판례를 검색합니다. 유사한 사건의 판결, 대법원 판례, 하급심 판결 등을 찾을 때 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색할 판례 관련 키워드 또는 쟁점"
                },
                "case_type": {
                    "type": "string",
                    "enum": ["civil", "criminal", "administrative", "family", "all"],
                    "description": "사건 유형",
                    "default": "all"
                },
                "top_k": {
                    "type": "integer",
                    "description": "반환할 판례 수",
                    "default": 5
                }
            },
            "required": ["query"]
        },
        "workflow_name": "rag_workflow",
        "category": "search"
    },

    "search_statutes": {
        "name": "search_statutes",
        "description": "법령/법률 조문을 검색합니다. 특정 법률의 조항, 시행령, 시행규칙 등을 찾을 때 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색할 법령 키워드 (예: '민법 제750조', '형법 절도죄')"
                },
                "law_type": {
                    "type": "string",
                    "enum": ["civil", "criminal", "commercial", "administrative", "labor", "tax", "all"],
                    "description": "법령 분야",
                    "default": "all"
                }
            },
            "required": ["query"]
        },
        "workflow_name": "rag_workflow",
        "category": "search"
    },

    "search_user_documents": {
        "name": "search_user_documents",
        "description": "사용자가 업로드한 문서에서 검색합니다. '내 문서에서 찾아줘', '업로드한 계약서에서 검색' 등의 요청에 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색할 내용"
                },
                "document_id": {
                    "type": "string",
                    "description": "특정 문서 ID (선택사항, 없으면 모든 문서에서 검색)"
                },
                "top_k": {
                    "type": "integer",
                    "description": "반환할 결과 수",
                    "default": 5
                }
            },
            "required": ["query"]
        },
        "workflow_name": None,
        "category": "search",
        "is_external": True
    },

    # =========================================================================
    # 문서 분석 도구
    # =========================================================================
    "analyze_document": {
        "name": "analyze_document",
        "description": "문서를 분석합니다. 계약서, 소장, 판결문 등의 요약, 핵심 조항 추출, 리스크 분석에 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "분석할 문서 내용"
                },
                "doc_type": {
                    "type": "string",
                    "enum": ["CONTRACT", "COMPLAINT", "JUDGMENT", "STATUTE", "OTHER"],
                    "description": "문서 유형",
                    "default": "OTHER"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["summary", "clauses", "risk", "full"],
                    "description": "분석 유형 (summary: 요약만, clauses: 조항 추출, risk: 리스크 분석, full: 전체)",
                    "default": "full"
                }
            },
            "required": ["content"]
        },
        "workflow_name": "document_workflow",
        "category": "analysis"
    },

    "analyze_case": {
        "name": "analyze_case",
        "description": "사건/판례를 분석합니다. 쟁점 파악, 당사자 관계, 판결 요지, 시사점 분석에 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_content": {
                    "type": "string",
                    "description": "분석할 사건 또는 판례 내용"
                },
                "case_type": {
                    "type": "string",
                    "enum": ["civil", "criminal", "administrative", "family"],
                    "description": "사건 유형",
                    "default": "civil"
                }
            },
            "required": ["case_content"]
        },
        "workflow_name": "case_workflow",
        "category": "analysis"
    },

    "analyze_risk": {
        "name": "analyze_risk",
        "description": "법률 문서의 리스크를 분석합니다. 잠재적 위험 요소, 불리한 조항, 주의사항을 파악합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "리스크 분석할 문서 내용"
                },
                "context": {
                    "type": "string",
                    "description": "추가 맥락 정보 (예: '을의 입장에서')",
                    "default": ""
                }
            },
            "required": ["content"]
        },
        "workflow_name": "risk_workflow",
        "category": "analysis"
    },

    # =========================================================================
    # 형사법 특화 도구
    # =========================================================================
    "analyze_criminal_case": {
        "name": "analyze_criminal_case",
        "description": "형사 사건을 종합 분석합니다. 범죄 유형 판단, 구성요건 분석, 양형인자 추출, 예상 형량 산정, 변호 전략 수립을 수행합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_content": {
                    "type": "string",
                    "description": "분석할 형사 사건 내용"
                },
                "crime_type": {
                    "type": "string",
                    "description": "범죄 유형 (선택사항, 미입력시 자동 감지)",
                    "default": ""
                }
            },
            "required": ["case_content"]
        },
        "workflow_name": "criminal_workflow",
        "category": "analysis"
    },

    "detect_crime_type": {
        "name": "detect_crime_type",
        "description": "사건 내용에서 범죄 유형을 감지합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_content": {
                    "type": "string",
                    "description": "분석할 사건 내용"
                }
            },
            "required": ["case_content"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    "analyze_crime_elements": {
        "name": "analyze_crime_elements",
        "description": "범죄의 구성요건을 분석합니다. 객관적 구성요건과 주관적 구성요건을 파악합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_content": {
                    "type": "string",
                    "description": "분석할 사건 내용"
                },
                "crime_type": {
                    "type": "string",
                    "description": "범죄 유형"
                }
            },
            "required": ["case_content", "crime_type"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    "extract_sentencing_factors": {
        "name": "extract_sentencing_factors",
        "description": "양형인자를 추출합니다. 유리한 정상과 불리한 정상을 분류합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_content": {
                    "type": "string",
                    "description": "분석할 사건 내용"
                },
                "crime_type": {
                    "type": "string",
                    "description": "범죄 유형"
                }
            },
            "required": ["case_content", "crime_type"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    "estimate_sentence": {
        "name": "estimate_sentence",
        "description": "예상 형량을 산정합니다. 양형기준에 따른 형량 범위와 예상 선고를 제시합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_content": {
                    "type": "string",
                    "description": "분석할 사건 내용"
                },
                "crime_type": {
                    "type": "string",
                    "description": "범죄 유형"
                },
                "sentencing_factors": {
                    "type": "object",
                    "description": "양형인자 (선택사항)",
                    "default": {}
                }
            },
            "required": ["case_content", "crime_type"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    "suggest_defense_strategies": {
        "name": "suggest_defense_strategies",
        "description": "변호 전략을 제안합니다. 무죄/감형을 위한 법적 논거와 전략을 수립합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_content": {
                    "type": "string",
                    "description": "분석할 사건 내용"
                },
                "crime_type": {
                    "type": "string",
                    "description": "범죄 유형"
                },
                "goal": {
                    "type": "string",
                    "enum": ["acquittal", "mitigation", "both"],
                    "description": "변호 목표 (무죄/감형/둘 다)",
                    "default": "both"
                }
            },
            "required": ["case_content", "crime_type"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    # =========================================================================
    # 사용자 데이터 조회 도구
    # =========================================================================
    "list_user_documents": {
        "name": "list_user_documents",
        "description": "사용자가 업로드한 문서 목록을 조회합니다. '내 문서 목록', '업로드한 문서 보여줘' 등의 요청에 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "enum": ["CASE", "CONTRACT", "STATUTE", "PRECEDENT", "OTHER", "all"],
                    "description": "문서 유형 필터",
                    "default": "all"
                },
                "search": {
                    "type": "string",
                    "description": "제목 검색어"
                },
                "limit": {
                    "type": "integer",
                    "description": "조회할 문서 수",
                    "default": 10
                }
            },
            "required": []
        },
        "workflow_name": None,
        "category": "search",
        "is_external": True,
        "requires_user_context": True
    },

    "list_user_criminal_cases": {
        "name": "list_user_criminal_cases",
        "description": "[레거시] 사용자의 형사 사건 목록을 조회합니다. query_user_criminal_cases를 사용하세요.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "조회할 사건 수",
                    "default": 10
                }
            },
            "required": []
        },
        "workflow_name": None,
        "category": "search",
        "is_external": True,
        "requires_user_context": True
    },

    "query_user_criminal_cases": {
        "name": "query_user_criminal_cases",
        "description": """사용자의 형사 사건을 유연하게 조회합니다. 다양한 조건으로 검색할 수 있습니다.

사용 예시:
- "내 사건 목록": order_by="created_at"
- "형량이 가장 적은 사건": order_by="expected_sentence_score", order="asc", limit=1
- "형량이 가장 높은 사건": order_by="expected_sentence_score", order="desc", limit=1
- "절도 사건만 보여줘": crime_type_filter="절도"
- "수사 중인 사건들": stage_filter="INVESTIGATION"
""",
        "parameters": {
            "type": "object",
            "properties": {
                "order_by": {
                    "type": "string",
                    "enum": ["created_at", "expected_sentence_score", "case_name", "crime_type"],
                    "description": "정렬 기준 (created_at: 생성일, expected_sentence_score: 형량 심각도)",
                    "default": "created_at"
                },
                "order": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "정렬 순서 (asc: 오름차순, desc: 내림차순)",
                    "default": "desc"
                },
                "limit": {
                    "type": "integer",
                    "description": "반환할 결과 수",
                    "default": 10
                },
                "crime_type_filter": {
                    "type": "string",
                    "description": "범죄 유형 필터 (예: 절도, 사기, 폭행)"
                },
                "stage_filter": {
                    "type": "string",
                    "enum": ["COMPLAINT", "INVESTIGATION", "PROSECUTION", "TRIAL", "JUDGMENT", "CLOSED"],
                    "description": "진행 단계 필터"
                }
            },
            "required": []
        },
        "workflow_name": None,
        "category": "search",
        "is_external": True,
        "requires_user_context": True
    },

    "get_criminal_case_detail": {
        "name": "get_criminal_case_detail",
        "description": "특정 형사 사건의 상세 정보를 조회합니다. 구성요건, 양형인자, 예상 양형, 변호 전략 등 전체 정보를 가져옵니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_id": {
                    "type": "string",
                    "description": "사건 ID (UUID)"
                }
            },
            "required": ["case_id"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True,
        "requires_user_context": True
    },

    "get_user_case_statistics": {
        "name": "get_user_case_statistics",
        "description": "사용자의 형사 사건 통계를 조회합니다. 전체 사건 수, 단계별/범죄유형별 분포, 양형 통계 (가장 높은/낮은 형량 사건) 등을 제공합니다.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True,
        "requires_user_context": True
    },

    "get_document_analysis": {
        "name": "get_document_analysis",
        "description": "특정 문서의 분석 결과를 조회합니다. 이미 분석된 문서의 요약, 리스크, 사건 분석 결과를 가져옵니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "문서 ID"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["summary", "risk", "case", "all"],
                    "description": "조회할 분석 유형",
                    "default": "all"
                }
            },
            "required": ["document_id"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True,
        "requires_user_context": True
    },

    "get_risk_overview": {
        "name": "get_risk_overview",
        "description": "사용자 문서의 전체 리스크 현황을 조회합니다. 리스크 분포, 평균 점수, 고위험 문서 수 등을 제공합니다.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True,
        "requires_user_context": True
    },

    # =========================================================================
    # MCP 도구 (Phase 7: LLM Native Tool Use 확장)
    # =========================================================================

    # --- 판례 도구 ---
    "get_precedent_details": {
        "name": "get_precedent_details",
        "description": "특정 판례의 상세 정보를 조회합니다. 사건번호로 판결문 전문, 주요 판시사항, 참조조문 등을 가져옵니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_number": {
                    "type": "string",
                    "description": "사건번호 (예: '2020도1234', '2019다12345')"
                }
            },
            "required": ["case_number"]
        },
        "workflow_name": None,
        "category": "search",
        "is_external": True
    },

    # --- 문서 분석 도구 ---
    "extract_clauses": {
        "name": "extract_clauses",
        "description": "문서에서 조항을 추출합니다. 계약서, 약관, 법령 등에서 개별 조항을 분리하여 반환합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "조항을 추출할 문서 내용"
                }
            },
            "required": ["content"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    "summarize_document": {
        "name": "summarize_document",
        "description": "문서를 요약합니다. 긴 법률 문서, 판결문, 계약서 등의 핵심 내용을 간결하게 정리합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "요약할 문서 내용"
                },
                "max_length": {
                    "type": "integer",
                    "description": "요약 최대 길이 (글자 수)",
                    "default": 500
                }
            },
            "required": ["content"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    "detect_document_type": {
        "name": "detect_document_type",
        "description": "문서 타입을 자동 감지합니다. 계약서, 판결문, 소장, 법령 등 문서 유형을 판별합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "타입을 감지할 문서 내용"
                }
            },
            "required": ["content"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    # --- 사건 분석 도구 ---
    "extract_parties": {
        "name": "extract_parties",
        "description": "사건에서 당사자를 추출합니다. 원고, 피고, 피해자, 피의자 등 관련자 정보를 식별합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_content": {
                    "type": "string",
                    "description": "당사자를 추출할 사건 내용"
                }
            },
            "required": ["case_content"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    "identify_issues": {
        "name": "identify_issues",
        "description": "사건의 법적 쟁점을 식별합니다. 사실관계와 법률적 쟁점을 분류하여 제시합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_content": {
                    "type": "string",
                    "description": "쟁점을 식별할 사건 내용"
                }
            },
            "required": ["case_content"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    "search_related_cases": {
        "name": "search_related_cases",
        "description": "관련 사건을 검색합니다. 유사한 쟁점이나 사실관계를 가진 선례를 찾습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색 질의"
                },
                "case_type": {
                    "type": "string",
                    "enum": ["civil", "criminal", "administrative", "family", "all"],
                    "description": "사건 유형 필터",
                    "default": "all"
                },
                "top_k": {
                    "type": "integer",
                    "description": "반환할 결과 수",
                    "default": 5
                }
            },
            "required": ["query"]
        },
        "workflow_name": None,
        "category": "search",
        "is_external": True
    },

    "assess_case_complexity": {
        "name": "assess_case_complexity",
        "description": "사건 복잡도를 평가합니다. 쟁점 수, 증거 복잡성, 법적 난이도 등을 분석합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_content": {
                    "type": "string",
                    "description": "복잡도를 평가할 사건 내용"
                }
            },
            "required": ["case_content"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    # --- 분석 도구 ---
    "analyze_risks": {
        "name": "analyze_risks",
        "description": "문서의 리스크를 분석합니다. 계약 조건의 위험성, 법적 취약점 등을 평가합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "리스크를 분석할 문서 내용"
                },
                "doc_type": {
                    "type": "string",
                    "enum": ["contract", "agreement", "terms", "other"],
                    "description": "문서 유형",
                    "default": "contract"
                }
            },
            "required": ["content"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    "compare_documents": {
        "name": "compare_documents",
        "description": "두 문서를 비교합니다. 조항 차이, 누락 사항, 변경점 등을 분석합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "doc1": {
                    "type": "string",
                    "description": "첫 번째 문서 내용"
                },
                "doc2": {
                    "type": "string",
                    "description": "두 번째 문서 내용"
                },
                "comparison_type": {
                    "type": "string",
                    "enum": ["similarity", "difference", "full"],
                    "description": "비교 유형",
                    "default": "similarity"
                }
            },
            "required": ["doc1", "doc2"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    "generate_report": {
        "name": "generate_report",
        "description": "분석 결과로 보고서를 생성합니다. 분석 내용을 정리된 형태로 출력합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "analysis_results": {
                    "type": "object",
                    "description": "분석 결과 데이터"
                },
                "report_type": {
                    "type": "string",
                    "enum": ["summary", "detailed", "executive"],
                    "description": "보고서 유형",
                    "default": "summary"
                }
            },
            "required": ["analysis_results"]
        },
        "workflow_name": None,
        "category": "analysis",
        "is_external": True
    },

    # --- 외부 API 도구 ---
    "fetch_court_api": {
        "name": "fetch_court_api",
        "description": "대법원 판례 API를 호출합니다. 국가법령정보센터에서 실시간 판례 데이터를 조회합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_number": {
                    "type": "string",
                    "description": "사건번호 (예: '2020도1234')"
                },
                "keyword": {
                    "type": "string",
                    "description": "검색 키워드"
                },
                "start_date": {
                    "type": "string",
                    "description": "선고일자 시작 (YYYY-MM-DD)"
                },
                "end_date": {
                    "type": "string",
                    "description": "선고일자 종료 (YYYY-MM-DD)"
                },
                "court": {
                    "type": "string",
                    "description": "법원명 (예: '대법원')"
                },
                "page": {
                    "type": "integer",
                    "description": "페이지 번호",
                    "default": 1
                },
                "display": {
                    "type": "integer",
                    "description": "결과 개수",
                    "default": 20
                }
            },
            "required": []
        },
        "workflow_name": None,
        "category": "search",
        "is_external": True
    },

    "fetch_statute_api": {
        "name": "fetch_statute_api",
        "description": "법령 API를 호출합니다. 국가법령정보센터에서 최신 법령 정보를 조회합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "law_code": {
                    "type": "string",
                    "description": "법령 MST 코드"
                },
                "keyword": {
                    "type": "string",
                    "description": "검색 키워드"
                },
                "law_type": {
                    "type": "string",
                    "description": "법령 종류 (법률, 시행령, 시행규칙 등)"
                },
                "ministry": {
                    "type": "string",
                    "description": "소관부처"
                },
                "page": {
                    "type": "integer",
                    "description": "페이지 번호",
                    "default": 1
                },
                "display": {
                    "type": "integer",
                    "description": "결과 개수",
                    "default": 20
                }
            },
            "required": []
        },
        "workflow_name": None,
        "category": "search",
        "is_external": True
    },

    "parse_legal_document": {
        "name": "parse_legal_document",
        "description": "법률 문서를 파싱합니다. 문서 구조를 분석하고 주요 섹션을 추출합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "파싱할 문서 내용 (HTML 또는 텍스트)"
                },
                "doc_type": {
                    "type": "string",
                    "enum": ["precedent", "statute", "contract", "unknown"],
                    "description": "문서 타입",
                    "default": "unknown"
                }
            },
            "required": ["content"]
        },
        "workflow_name": None,
        "category": "utility",
        "is_external": True
    },

    "validate_document_structure": {
        "name": "validate_document_structure",
        "description": "문서 구조를 검증합니다. 필수 필드 존재 여부를 확인합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "검증할 문서 데이터"
                },
                "doc_type": {
                    "type": "string",
                    "enum": ["precedent", "statute", "contract"],
                    "description": "문서 타입",
                    "default": "precedent"
                }
            },
            "required": ["data"]
        },
        "workflow_name": None,
        "category": "utility",
        "is_external": True
    },
}


# =============================================================================
# Agent Hub에서 기본으로 사용할 도구 목록
# =============================================================================

DEFAULT_AGENT_TOOLS = [
    # 검색 (가장 많이 사용)
    "search_legal",
    "search_precedents",
    "search_statutes",
    "search_related_cases",

    # 판례 상세 조회
    "get_precedent_details",

    # 문서 분석
    "analyze_document",
    "analyze_case",
    "analyze_risk",
    "extract_clauses",
    "summarize_document",
    "detect_document_type",

    # 사건 분석
    "extract_parties",
    "identify_issues",
    "assess_case_complexity",

    # 형사법 특화
    "analyze_criminal_case",

    # 리스크/비교/보고서
    "analyze_risks",
    "compare_documents",
    "generate_report",

    # 외부 API
    "fetch_court_api",
    "fetch_statute_api",
    "parse_legal_document",
    "validate_document_structure",

    # 사용자 데이터 (user_context 필요)
    "list_user_documents",
    "search_user_documents",
    "get_document_analysis",

    # 사용자 형사 사건 조회 (Generic DB Query)
    "query_user_criminal_cases",
    "get_criminal_case_detail",
    "get_user_case_statistics",
]


# =============================================================================
# 변환 함수
# =============================================================================

def get_openai_tools(tool_names: List[str] = None) -> List[Dict[str, Any]]:
    """
    OpenAI tools 형식으로 도구 정의 반환

    Args:
        tool_names: 포함할 도구 이름 목록 (None이면 DEFAULT_AGENT_TOOLS 사용)

    Returns:
        OpenAI tools 형식의 도구 정의 목록
    """
    if tool_names is None:
        tool_names = DEFAULT_AGENT_TOOLS

    tools = []
    for name in tool_names:
        if name in TOOL_SCHEMAS:
            schema = TOOL_SCHEMAS[name]
            tools.append({
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema["description"],
                    "parameters": schema["parameters"]
                }
            })

    return tools


def get_anthropic_tools(tool_names: List[str] = None) -> List[Dict[str, Any]]:
    """
    Anthropic tools 형식으로 도구 정의 반환

    Args:
        tool_names: 포함할 도구 이름 목록 (None이면 DEFAULT_AGENT_TOOLS 사용)

    Returns:
        Anthropic tools 형식의 도구 정의 목록
    """
    if tool_names is None:
        tool_names = DEFAULT_AGENT_TOOLS

    tools = []
    for name in tool_names:
        if name in TOOL_SCHEMAS:
            schema = TOOL_SCHEMAS[name]
            tools.append({
                "name": schema["name"],
                "description": schema["description"],
                "input_schema": schema["parameters"]
            })

    return tools


def get_tool_schema(tool_name: str) -> Dict[str, Any]:
    """특정 도구의 스키마 반환"""
    return TOOL_SCHEMAS.get(tool_name, {})


def get_tools_by_category(category: str) -> List[str]:
    """카테고리별 도구 이름 반환"""
    return [
        name for name, schema in TOOL_SCHEMAS.items()
        if schema.get("category") == category
    ]


# =============================================================================
# 동적 도구 선택 (Phase 2)
# =============================================================================

# 질문 유형별 도구 매핑
QUERY_TYPE_TOOLS = {
    "statute": ["search_statutes", "search_legal", "fetch_statute_api"],
    "precedent": ["search_precedents", "search_legal", "get_precedent_details", "fetch_court_api"],
    "document_analysis": ["analyze_document", "analyze_risk", "extract_clauses", "summarize_document", "detect_document_type"],
    "case_analysis": ["analyze_case", "analyze_criminal_case", "extract_parties", "identify_issues", "assess_case_complexity"],
    "criminal": ["analyze_criminal_case", "search_precedents", "search_related_cases"],
    "user_data": ["list_user_documents", "search_user_documents", "get_document_analysis"],
    "user_criminal_cases": ["query_user_criminal_cases", "get_criminal_case_detail", "get_user_case_statistics"],
    "risk": ["analyze_risk", "analyze_risks", "get_risk_overview", "list_documents_with_risk"],
    "comparison": ["compare_documents"],
    "report": ["generate_report"],
    "external_api": ["fetch_court_api", "fetch_statute_api"],
    "parsing": ["parse_legal_document", "validate_document_structure"],
    "general_legal": ["search_legal"],
}

# 키워드 → 질문 유형 매핑
KEYWORD_TO_QUERY_TYPE = {
    # 법령 관련
    "법령": "statute", "조문": "statute", "조항": "statute",
    "민법": "statute", "형법": "statute", "상법": "statute",
    "근로기준법": "statute", "제": "statute",
    "법률": "statute", "시행령": "statute", "시행규칙": "statute",

    # 판례 관련
    "판례": "precedent", "판결": "precedent", "대법원": "precedent",
    "선고": "precedent", "사건번호": "precedent",
    "판시사항": "precedent", "헌법재판소": "precedent",

    # 문서 분석
    "분석해": "document_analysis", "검토해": "document_analysis",
    "계약서": "document_analysis", "요약해": "document_analysis",
    "조항 추출": "document_analysis", "문서 타입": "document_analysis",
    "요약": "document_analysis",

    # 사건 분석
    "사건": "case_analysis", "당사자": "case_analysis",
    "쟁점": "case_analysis", "복잡도": "case_analysis",
    "원고": "case_analysis", "피고": "case_analysis",

    # 형사법
    "형사": "criminal", "범죄": "criminal", "절도": "criminal",
    "사기": "criminal", "폭행": "criminal", "양형": "criminal",
    "기소": "criminal", "피의자": "criminal", "피해자": "criminal",

    # 사용자 형사 사건 조회 (형량 관련 질문 포함)
    "내 사건": "user_criminal_cases", "내 형사 사건": "user_criminal_cases",
    "형량이 가장": "user_criminal_cases", "형량이 제일": "user_criminal_cases",
    "가장 적은": "user_criminal_cases", "가장 낮은": "user_criminal_cases",
    "가장 높은": "user_criminal_cases", "가장 무거운": "user_criminal_cases",
    "사건 목록": "user_criminal_cases", "사건 통계": "user_criminal_cases",

    # 사용자 문서 데이터
    "내 문서": "user_data", "업로드한": "user_data", "등록한": "user_data",

    # 리스크
    "리스크": "risk", "위험": "risk", "위험도": "risk",
    "취약점": "risk", "불리한": "risk",

    # 비교
    "비교해": "comparison", "비교": "comparison", "차이점": "comparison",

    # 보고서
    "보고서": "report", "리포트": "report",

    # 외부 API
    "국가법령정보센터": "external_api", "최신 판례": "external_api",
    "최신 법령": "external_api", "실시간": "external_api",

    # 파싱/검증
    "파싱": "parsing", "검증": "parsing", "구조 분석": "parsing",
}


def select_tools_for_query(
    query: str,
    has_attachment: bool = False,
    has_user_context: bool = False,
    max_tools: int = 6,
) -> List[str]:
    """
    질문에 적합한 도구 동적 선택

    Args:
        query: 사용자 질문
        has_attachment: 첨부 파일 존재 여부
        has_user_context: 사용자 컨텍스트 존재 여부
        max_tools: 최대 도구 수

    Returns:
        선택된 도구 이름 목록
    """
    query_lower = query.lower()
    selected_types = set()

    # 키워드 기반 질문 유형 식별
    for keyword, query_type in KEYWORD_TO_QUERY_TYPE.items():
        if keyword in query_lower:
            selected_types.add(query_type)

    # 첨부 파일이 있으면 문서 분석 추가
    if has_attachment:
        selected_types.add("document_analysis")

    # 질문 유형이 식별되지 않으면 일반 법률 검색
    if not selected_types:
        selected_types.add("general_legal")

    # 도구 수집
    selected_tools = set()
    for query_type in selected_types:
        tools = QUERY_TYPE_TOOLS.get(query_type, [])
        selected_tools.update(tools)

    # 사용자 컨텍스트가 없으면 사용자 데이터 도구 제외
    if not has_user_context:
        selected_tools = {t for t in selected_tools if not t.startswith("list_user") and not t.startswith("get_")}

    # search_legal은 항상 포함 (폴백용)
    selected_tools.add("search_legal")

    return list(selected_tools)[:max_tools]
