"""
LangGraph Workflow Definitions

Phase 4 - Week 11-12: LangGraph 기반 워크플로우

워크플로우 목록:
- RAGWorkflow: RAG 기반 질의응답 (Checkpointing 불필요)
- DocumentWorkflow: 문서 분석 (Checkpointing 불필요)
- CaseWorkflow: 사건 분석 (Checkpointing 불필요)
- RiskWorkflow: 리스크 분석 (Checkpointing 필수 - Human-in-the-Loop)
"""

# 지연 import로 순환 참조 방지


def get_rag_workflow():
    """RAG Workflow 인스턴스 반환"""
    from apps.ai_service.workflows.rag_workflow import RAGWorkflow
    return RAGWorkflow()


def create_rag_workflow():
    """RAG Workflow StateGraph 생성"""
    from apps.ai_service.workflows.rag_workflow import create_rag_workflow as _create
    return _create()


def get_document_workflow():
    """Document Workflow 인스턴스 반환"""
    from apps.ai_service.workflows.document_workflow import DocumentWorkflow
    return DocumentWorkflow()


def create_document_workflow():
    """Document Workflow StateGraph 생성"""
    from apps.ai_service.workflows.document_workflow import (
        create_document_workflow as _create
    )
    return _create()


def get_case_workflow():
    """Case Workflow 인스턴스 반환"""
    from apps.ai_service.workflows.case_workflow import CaseWorkflow
    return CaseWorkflow()


def create_case_workflow():
    """Case Workflow StateGraph 생성"""
    from apps.ai_service.workflows.case_workflow import (
        create_case_workflow as _create
    )
    return _create()


def get_risk_workflow():
    """Risk Workflow 인스턴스 반환 (Checkpointing 포함)"""
    from apps.ai_service.workflows.risk_workflow import RiskWorkflow
    return RiskWorkflow()


def create_risk_workflow(use_checkpointing: bool = True):
    """Risk Workflow StateGraph 생성"""
    from apps.ai_service.workflows.risk_workflow import (
        create_risk_workflow as _create
    )
    return _create(use_checkpointing=use_checkpointing)


__all__ = [
    "get_rag_workflow",
    "create_rag_workflow",
    "get_document_workflow",
    "create_document_workflow",
    "get_case_workflow",
    "create_case_workflow",
    "get_risk_workflow",
    "create_risk_workflow",
]
