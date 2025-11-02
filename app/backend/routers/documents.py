"""
Documents Router
문서 생성 관련 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import logging
import json
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


def validate_uuid(id_string: str, field_name: str = "ID") -> str:
    """
    UUID 형식 검증

    경로 탐색 공격 방지
    """
    try:
        uuid_obj = uuid.UUID(id_string)
        validated_id = str(uuid_obj)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name} format"
        )

    # 추가 보안 검증
    if '..' in id_string or '/' in id_string or '\\' in id_string:
        logger.warning(f"Path traversal attempt in {field_name}: {id_string}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}"
        )

    return validated_id


class DocumentGenerationRequest(BaseModel):
    case_id: str
    template_name: str
    generation_mode: Optional[str] = "quick"
    custom_fields: Optional[Dict[str, str]] = None
    user_instructions: Optional[str] = None


class DocumentGenerationResponse(BaseModel):
    document_id: str
    title: str
    content: str
    template_used: str
    metadata: Dict[str, Any]


def setup_document_routes(
    document_generator,
    scenario_detector,
    upload_dir: Path
):
    """문서 생성 라우트 설정"""

    @router.post("/generate", response_model=DocumentGenerationResponse)
    async def generate_document(request: DocumentGenerationRequest):
        """템플릿 기반 법률 문서 생성"""
        if not document_generator:
            raise HTTPException(status_code=503, detail="Document generator not available")

        try:
            # Case ID 검증
            validated_case_id = validate_uuid(request.case_id, "case_id")

            case_dir = upload_dir / validated_case_id
            analysis_path = case_dir / "analysis.json"

            # 경로 정규화 및 검증
            resolved_path = analysis_path.resolve()
            if not str(resolved_path).startswith(str(upload_dir.resolve())):
                logger.error(f"Path traversal attempt: {resolved_path}")
                raise HTTPException(status_code=400, detail="Invalid path")

            if not analysis_path.exists():
                raise HTTPException(status_code=404, detail="Case not found")

            with open(analysis_path, "r", encoding="utf-8") as f:
                case_analysis = json.load(f)

            logger.info(f"Generating document '{request.template_name}' for case {request.case_id} (mode: {request.generation_mode})")
            document = await document_generator.generate_document(
                template_name=request.template_name,
                case_analysis=case_analysis,
                generation_mode=request.generation_mode,
                custom_fields=request.custom_fields,
                user_instructions=request.user_instructions
            )

            document_id = str(uuid.uuid4())
            documents_dir = case_dir / "documents"
            documents_dir.mkdir(exist_ok=True)

            document_path = documents_dir / f"{document_id}.json"
            document_with_id = {
                "document_id": document_id,
                "created_at": datetime.now().isoformat(),
                **document
            }

            with open(document_path, "w", encoding="utf-8") as f:
                json.dump(document_with_id, f, ensure_ascii=False, indent=2)

            logger.info(f"Document generated and saved: {document_id}")

            return DocumentGenerationResponse(
                document_id=document_id,
                title=document["title"],
                content=document["content"],
                template_used=document["template_used"],
                metadata=document["metadata"]
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Document generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/scenarios")
    async def list_scenarios():
        """사용 가능한 시나리오 및 템플릿 목록 조회"""
        return {"scenarios": scenario_detector.SCENARIOS}

    @router.get("/{case_id}/{document_id}")
    async def get_generated_document(case_id: str, document_id: str):
        """생성된 문서 조회"""
        try:
            # Case ID 및 Document ID 검증
            validated_case_id = validate_uuid(case_id, "case_id")
            validated_document_id = validate_uuid(document_id, "document_id")

            document_path = upload_dir / validated_case_id / "documents" / f"{validated_document_id}.json"

            # 경로 정규화 및 검증
            resolved_path = document_path.resolve()
            if not str(resolved_path).startswith(str(upload_dir.resolve())):
                logger.error(f"Path traversal attempt: {resolved_path}")
                raise HTTPException(status_code=400, detail="Invalid path")

            if not document_path.exists():
                raise HTTPException(status_code=404, detail="Document not found")

            with open(document_path, "r", encoding="utf-8") as f:
                document = json.load(f)

            return document

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get document error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/{case_id}")
    async def list_generated_documents(case_id: str):
        """사건의 모든 생성 문서 목록 조회"""
        try:
            # Case ID 검증
            validated_case_id = validate_uuid(case_id, "case_id")

            documents_dir = upload_dir / validated_case_id / "documents"

            # 경로 정규화 및 검증
            resolved_dir = documents_dir.resolve()
            if not str(resolved_dir).startswith(str(upload_dir.resolve())):
                logger.error(f"Path traversal attempt: {resolved_dir}")
                raise HTTPException(status_code=400, detail="Invalid path")

            if not documents_dir.exists():
                return {"documents": [], "total": 0}

            documents = []
            for doc_file in documents_dir.glob("*.json"):
                with open(doc_file, "r", encoding="utf-8") as f:
                    doc = json.load(f)
                    documents.append({
                        "document_id": doc.get("document_id"),
                        "title": doc.get("title"),
                        "template_used": doc.get("template_used"),
                        "created_at": doc.get("created_at")
                    })

            documents.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            return {"documents": documents, "total": len(documents)}

        except Exception as e:
            logger.error(f"List documents error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/{case_id}/{document_id}")
    async def delete_generated_document(case_id: str, document_id: str):
        """생성된 문서 삭제"""
        try:
            # Case ID 및 Document ID 검증
            validated_case_id = validate_uuid(case_id, "case_id")
            validated_document_id = validate_uuid(document_id, "document_id")

            document_path = upload_dir / validated_case_id / "documents" / f"{validated_document_id}.json"

            # 경로 정규화 및 검증
            resolved_path = document_path.resolve()
            if not str(resolved_path).startswith(str(upload_dir.resolve())):
                logger.error(f"Path traversal attempt: {resolved_path}")
                raise HTTPException(status_code=400, detail="Invalid path")

            if not document_path.exists():
                raise HTTPException(status_code=404, detail="Document not found")

            document_path.unlink()

            logger.info(f"Document deleted: {validated_document_id}")
            return {"success": True, "message": f"Document {validated_document_id} deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Delete document error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
