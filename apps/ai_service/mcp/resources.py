"""
MCP Resources for Legal SaaS

Phase 4 - Week 12: FastMCP 기반 MCP Resources 구현

MCP Resources는 LLM이 필요 시 직접 데이터를 읽을 수 있게 합니다.

리소스 목록:
- document://{doc_id}/text - 문서 원문 조회
- document://{doc_id}/metadata - 문서 메타데이터
- document://{doc_id}/chunks - 문서 청크 목록
- precedent://{case_number} - 판례 원문 조회
- precedent://{case_number}/metadata - 판례 메타데이터

사용 예:
    from mcp.resources import mcp_resources

    # MCP 서버 등록
    app.mount("/mcp", mcp_resources.sse_app())

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""

import os
import sys
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

# Django 설정을 위한 환경 변수
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_api.settings')

# Django Setup (AI Service에서 Django 모델 접근 시)
import django
django.setup()

from asgiref.sync import sync_to_async
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# FastMCP 서버 인스턴스 (naked decorator 사용 - FastMCP 2.7+)
mcp_resources = FastMCP(
    name="constitutional-law-resources",
    instructions="""
    이 MCP 서버는 법률 SaaS 시스템의 문서 및 판례 리소스를 제공합니다.

    사용 가능한 리소스:
    1. document://{doc_id}/text - 문서 원문 (청크 결합)
    2. document://{doc_id}/metadata - 문서 메타데이터 (타입, 상태, 생성일 등)
    3. document://{doc_id}/chunks - 문서 청크 목록 (벡터 검색용)
    4. precedent://{case_number} - 판례 전문 (대법원 판례)
    5. precedent://{case_number}/metadata - 판례 메타데이터 (법원, 선고일 등)

    리소스 URI는 해당 ID나 사건번호를 알고 있어야 사용할 수 있습니다.
    """
)


# ============================================================================
# Document Resources
# ============================================================================

@mcp_resources.resource("document://{doc_id}/text")
async def get_document_text(doc_id: str) -> str:
    """
    문서 원문 조회 (청크 결합)

    LLM이 문서 전체 내용을 읽어야 할 때 사용합니다.

    Args:
        doc_id: 문서 UUID

    Returns:
        문서 전체 텍스트 (청크 결합)
    """
    from documents.models import Document, DocumentChunk

    try:
        # Django ORM을 async로 래핑
        @sync_to_async
        def fetch_document_text(document_id: str) -> str:
            try:
                doc = Document.objects.get(id=document_id)
                chunks = DocumentChunk.objects.filter(document=doc).order_by('chunk_index')

                if not chunks.exists():
                    return f"[문서 ID: {document_id}]\n[제목: {doc.title}]\n\n(청크 데이터 없음 - 원본 파일 처리 필요)"

                # 청크 텍스트 결합
                full_text = "\n\n".join([chunk.text for chunk in chunks])

                return f"""[문서 ID: {document_id}]
[제목: {doc.title}]
[유형: {doc.get_doc_type_display()}]
[상태: {doc.get_status_display()}]

--- 문서 내용 ---

{full_text}
"""
            except Document.DoesNotExist:
                return f"[오류] 문서를 찾을 수 없습니다: {document_id}"
            except Exception as e:
                logger.error(f"문서 조회 실패: {e}")
                return f"[오류] 문서 조회 중 오류 발생: {str(e)}"

        return await fetch_document_text(doc_id)

    except Exception as e:
        logger.error(f"get_document_text 실패: {e}")
        return f"[오류] 리소스 접근 실패: {str(e)}"


@mcp_resources.resource("document://{doc_id}/metadata")
async def get_document_metadata(doc_id: str) -> str:
    """
    문서 메타데이터 조회

    문서의 기본 정보(타입, 상태, 생성일 등)를 확인할 때 사용합니다.

    Args:
        doc_id: 문서 UUID

    Returns:
        JSON 형식 문서 메타데이터
    """
    from documents.models import Document

    try:
        @sync_to_async
        def fetch_metadata(document_id: str) -> str:
            try:
                doc = Document.objects.get(id=document_id)

                metadata = {
                    "id": str(doc.id),
                    "title": doc.title,
                    "doc_type": doc.doc_type,
                    "doc_type_display": doc.get_doc_type_display(),
                    "source_type": doc.source_type,
                    "source_type_display": doc.get_source_type_display(),
                    "status": doc.status,
                    "status_display": doc.get_status_display(),
                    "language": doc.language,
                    "file_size": doc.file_size,
                    "file_type": doc.file_type,
                    "page_count": doc.page_count,
                    "chunk_count": doc.chunk_count,
                    "is_processing_complete": doc.is_processing_complete,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                    "user_id": str(doc.user.id) if doc.user else None,
                }

                return json.dumps(metadata, ensure_ascii=False, indent=2)

            except Document.DoesNotExist:
                return json.dumps({"error": f"문서를 찾을 수 없습니다: {document_id}"})
            except Exception as e:
                logger.error(f"메타데이터 조회 실패: {e}")
                return json.dumps({"error": str(e)})

        return await fetch_metadata(doc_id)

    except Exception as e:
        logger.error(f"get_document_metadata 실패: {e}")
        return json.dumps({"error": str(e)})


@mcp_resources.resource("document://{doc_id}/chunks")
async def get_document_chunks(doc_id: str) -> str:
    """
    문서 청크 목록 조회

    문서의 개별 청크들을 확인할 때 사용합니다.
    벡터 검색 결과와 매핑 시 유용합니다.

    Args:
        doc_id: 문서 UUID

    Returns:
        JSON 형식 청크 목록
    """
    from documents.models import Document, DocumentChunk

    try:
        @sync_to_async
        def fetch_chunks(document_id: str) -> str:
            try:
                doc = Document.objects.get(id=document_id)
                chunks = DocumentChunk.objects.filter(document=doc).order_by('chunk_index')

                chunk_list = []
                for chunk in chunks:
                    chunk_list.append({
                        "id": str(chunk.id),
                        "chunk_index": chunk.chunk_index,
                        "text_preview": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                        "text_length": len(chunk.text),
                        "page_number": chunk.page_number,
                        "token_count": chunk.token_count,
                        "embedding_id": chunk.embedding_id,
                        "is_embedded": chunk.is_embedded,
                    })

                result = {
                    "document_id": str(doc.id),
                    "document_title": doc.title,
                    "total_chunks": len(chunk_list),
                    "chunks": chunk_list
                }

                return json.dumps(result, ensure_ascii=False, indent=2)

            except Document.DoesNotExist:
                return json.dumps({"error": f"문서를 찾을 수 없습니다: {document_id}"})
            except Exception as e:
                logger.error(f"청크 조회 실패: {e}")
                return json.dumps({"error": str(e)})

        return await fetch_chunks(doc_id)

    except Exception as e:
        logger.error(f"get_document_chunks 실패: {e}")
        return json.dumps({"error": str(e)})


# ============================================================================
# Precedent Resources
# ============================================================================

@mcp_resources.resource("precedent://{case_number}")
async def get_precedent(case_number: str) -> str:
    """
    판례 원문 조회

    대법원 판례의 전문을 읽을 때 사용합니다.

    Args:
        case_number: 사건번호 (예: "2023다12345")

    Returns:
        판례 전문 (Markdown 형식)
    """
    from precedents.models import Precedent

    try:
        @sync_to_async
        def fetch_precedent(case_num: str) -> str:
            try:
                # 사건번호로 검색 (정확 매치 또는 부분 매치)
                precedent = Precedent.objects.filter(case_number__icontains=case_num).first()

                if not precedent:
                    # 정확 매치 시도
                    precedent = Precedent.objects.filter(case_number=case_num).first()

                if not precedent:
                    return f"[오류] 판례를 찾을 수 없습니다: {case_num}"

                # 판례 전문 구성
                decision_date_str = precedent.decision_date.strftime('%Y.%m.%d') if precedent.decision_date else "날짜 정보 없음"

                content = f"""# {precedent.title}

## 기본 정보
- **사건번호**: {precedent.case_number}
- **법원**: {precedent.court}
- **선고일**: {decision_date_str}
- **사건종류**: {precedent.case_type}

## 요약
{precedent.summary or "(요약 없음)"}

## 판시사항
{precedent.judgment_summary or "(판시사항 없음)"}

## 판결 전문
{precedent.full_text or "(전문 없음)"}

"""

                # 참조조문/판례 추가 (JSON 문자열 파싱)
                try:
                    ref_statutes = json.loads(precedent.reference_statutes or '[]')
                    if ref_statutes:
                        content += f"\n## 참조조문\n"
                        for statute in ref_statutes:
                            content += f"- {statute}\n"
                except:
                    pass

                try:
                    ref_precedents = json.loads(precedent.reference_precedents or '[]')
                    if ref_precedents:
                        content += f"\n## 참조판례\n"
                        for ref in ref_precedents:
                            content += f"- {ref}\n"
                except:
                    pass

                return content

            except Exception as e:
                logger.error(f"판례 조회 실패: {e}")
                return f"[오류] 판례 조회 중 오류 발생: {str(e)}"

        return await fetch_precedent(case_number)

    except Exception as e:
        logger.error(f"get_precedent 실패: {e}")
        return f"[오류] 리소스 접근 실패: {str(e)}"


@mcp_resources.resource("precedent://{case_number}/metadata")
async def get_precedent_metadata(case_number: str) -> str:
    """
    판례 메타데이터 조회

    판례의 기본 정보(법원, 선고일, 사건종류 등)를 확인할 때 사용합니다.

    Args:
        case_number: 사건번호 (예: "2023다12345")

    Returns:
        JSON 형식 판례 메타데이터
    """
    from precedents.models import Precedent

    try:
        @sync_to_async
        def fetch_metadata(case_num: str) -> str:
            try:
                # 사건번호로 검색
                precedent = Precedent.objects.filter(case_number__icontains=case_num).first()

                if not precedent:
                    precedent = Precedent.objects.filter(case_number=case_num).first()

                if not precedent:
                    return json.dumps({"error": f"판례를 찾을 수 없습니다: {case_num}"})

                # 참조조문/판례 파싱
                try:
                    ref_statutes = json.loads(precedent.reference_statutes or '[]')
                except:
                    ref_statutes = []

                try:
                    ref_precedents = json.loads(precedent.reference_precedents or '[]')
                except:
                    ref_precedents = []

                try:
                    specialization_tags = json.loads(precedent.specialization_tags or '[]')
                except:
                    specialization_tags = []

                metadata = {
                    "id": str(precedent.id),
                    "case_number": precedent.case_number,
                    "title": precedent.title,
                    "court": precedent.court,
                    "case_type": precedent.case_type,
                    "decision_date": precedent.decision_date.isoformat() if precedent.decision_date else None,
                    "precedent_id": precedent.precedent_id,
                    "citation": precedent.citation,
                    "case_link": precedent.case_link,
                    "reference_statutes": ref_statutes,
                    "reference_precedents": ref_precedents,
                    "specialization_tags": specialization_tags,
                    "has_full_text": bool(precedent.full_text),
                    "has_summary": bool(precedent.summary),
                    "has_judgment_summary": bool(precedent.judgment_summary),
                    "created_at": precedent.created_at.isoformat() if precedent.created_at else None,
                    "updated_at": precedent.updated_at.isoformat() if precedent.updated_at else None,
                }

                return json.dumps(metadata, ensure_ascii=False, indent=2)

            except Exception as e:
                logger.error(f"판례 메타데이터 조회 실패: {e}")
                return json.dumps({"error": str(e)})

        return await fetch_metadata(case_number)

    except Exception as e:
        logger.error(f"get_precedent_metadata 실패: {e}")
        return json.dumps({"error": str(e)})


# ============================================================================
# Utility Resources
# ============================================================================

@mcp_resources.resource("document://list")
async def list_recent_documents() -> str:
    """
    최근 문서 목록 조회

    최근 생성된 문서 목록을 확인합니다 (최대 20개).

    Returns:
        JSON 형식 문서 목록
    """
    from documents.models import Document

    try:
        @sync_to_async
        def fetch_list() -> str:
            try:
                docs = Document.objects.all().order_by('-created_at')[:20]

                doc_list = []
                for doc in docs:
                    doc_list.append({
                        "id": str(doc.id),
                        "title": doc.title,
                        "doc_type": doc.doc_type,
                        "status": doc.status,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    })

                return json.dumps({
                    "total": len(doc_list),
                    "documents": doc_list
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                logger.error(f"문서 목록 조회 실패: {e}")
                return json.dumps({"error": str(e)})

        return await fetch_list()

    except Exception as e:
        logger.error(f"list_recent_documents 실패: {e}")
        return json.dumps({"error": str(e)})


@mcp_resources.resource("precedent://list")
async def list_recent_precedents() -> str:
    """
    최근 판례 목록 조회

    최근 등록된 판례 목록을 확인합니다 (최대 20개).

    Returns:
        JSON 형식 판례 목록
    """
    from precedents.models import Precedent

    try:
        @sync_to_async
        def fetch_list() -> str:
            try:
                precedents = Precedent.objects.all().order_by('-decision_date')[:20]

                prec_list = []
                for prec in precedents:
                    prec_list.append({
                        "id": str(prec.id),
                        "case_number": prec.case_number,
                        "title": prec.title[:100] + "..." if len(prec.title) > 100 else prec.title,
                        "court": prec.court,
                        "case_type": prec.case_type,
                        "decision_date": prec.decision_date.isoformat() if prec.decision_date else None,
                    })

                return json.dumps({
                    "total": len(prec_list),
                    "precedents": prec_list
                }, ensure_ascii=False, indent=2)

            except Exception as e:
                logger.error(f"판례 목록 조회 실패: {e}")
                return json.dumps({"error": str(e)})

        return await fetch_list()

    except Exception as e:
        logger.error(f"list_recent_precedents 실패: {e}")
        return json.dumps({"error": str(e)})


# Export the MCP server
__all__ = ["mcp_resources"]
