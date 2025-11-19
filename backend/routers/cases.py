"""
Cases Router
사건 관리 관련 엔드포인트
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path
import logging
import json
import uuid
import shutil
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cases", tags=["cases"])

# 보안 설정
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILES_PER_UPLOAD = 5
ALLOWED_FILENAME_PATTERN = re.compile(r'^[\w\-. ()\[\]가-힣]+$')  # 안전한 파일명만 허용


class UploadedFileInfo(BaseModel):
    filename: str
    size: int


class CaseAnalysisResponse(BaseModel):
    case_id: str
    summary: str
    document_types: List[str]
    issues: List[str]
    key_dates: Dict[str, str]
    parties: Dict[str, str]
    related_cases: List[Dict[str, Any]]
    suggested_case_name: str
    suggested_next_steps: List[str]
    uploaded_files: List[UploadedFileInfo]
    scenario: Dict[str, Any]


def setup_case_routes(
    case_analyzer,
    scenario_detector,
    file_parser,
    upload_dir: Path
):
    """사건 관리 라우트 설정"""

    def validate_filename(filename: str) -> str:
        """
        파일명 보안 검증 및 정규화

        - 경로 탐색 공격 방지 (../, ..\\ 등)
        - 특수문자 제거
        - 안전한 파일명으로 변환
        """
        # 빈 파일명 체크
        if not filename or filename.strip() == '':
            raise HTTPException(status_code=400, detail="Invalid filename: empty")

        # Path 객체로 변환하여 파일명만 추출 (경로 제거)
        safe_filename = Path(filename).name

        # 경로 탐색 시도 감지
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.warning(f"Path traversal attempt detected: {filename}")
            raise HTTPException(
                status_code=400,
                detail="Invalid filename: path traversal not allowed"
            )

        # 안전한 문자 패턴 검증
        if not ALLOWED_FILENAME_PATTERN.match(safe_filename):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid filename: {safe_filename}. Only alphanumeric, Korean, and -_.()[] are allowed"
            )

        # 파일명 길이 제한 (255자)
        if len(safe_filename) > 255:
            raise HTTPException(
                status_code=400,
                detail=f"Filename too long: max 255 characters"
            )

        return safe_filename

    def validate_file_extension(filename: str) -> str:
        """파일 확장자 검증"""
        file_ext = Path(filename).suffix.lower()

        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        return file_ext

    @router.post("", response_model=CaseAnalysisResponse)
    @router.post("/upload", response_model=CaseAnalysisResponse)
    async def upload_case_files(files: List[UploadFile] = File(...)):
        """사건 파일 업로드 및 분석"""
        if not case_analyzer:
            raise HTTPException(status_code=503, detail="Case analyzer not available")

        # 업로드 파일 개수 제한
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail="No files uploaded")

        if len(files) > MAX_FILES_PER_UPLOAD:
            raise HTTPException(
                status_code=400,
                detail=f"Too many files: max {MAX_FILES_PER_UPLOAD} files allowed"
            )

        try:
            case_id = str(uuid.uuid4())
            case_dir = upload_dir / case_id
            case_dir.mkdir(parents=True, exist_ok=True)

            texts = []
            filenames = []
            file_info = []

            for file in files:
                # 파일명 검증 및 정규화
                safe_filename = validate_filename(file.filename)

                # 확장자 검증
                validate_file_extension(safe_filename)

                # 파일 내용 읽기
                content = await file.read()

                # 파일 크기 검증
                if len(content) == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Empty file: {safe_filename}"
                    )

                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large: {safe_filename} ({len(content)/1024/1024:.1f}MB). Max {MAX_FILE_SIZE/1024/1024}MB"
                    )

                # 안전한 경로로 파일 저장 (경로 정규화)
                file_path = (case_dir / safe_filename).resolve()

                # 경로 탐색 공격 방지: case_dir 외부로 벗어나는지 확인
                if not str(file_path).startswith(str(case_dir.resolve())):
                    logger.error(f"Path traversal attempt: {file_path}")
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid file path"
                    )

                # 파일 저장
                with open(file_path, "wb") as f:
                    f.write(content)

                logger.info(f"File saved: {safe_filename} ({len(content)} bytes)")

                file_info.append({
                    "filename": safe_filename,
                    "size": len(content),
                    "path": str(file_path)
                })

                # 파일 파싱
                try:
                    text = file_parser.parse_file(str(file_path))
                    texts.append(text)
                    filenames.append(safe_filename)
                    logger.info(f"Successfully parsed {safe_filename}: {len(text)} characters")
                except Exception as e:
                    logger.error(f"Failed to parse {safe_filename}: {e}")
                    # 파싱 실패 시 업로드된 파일 정리
                    shutil.rmtree(case_dir, ignore_errors=True)
                    raise HTTPException(
                        status_code=500,
                        detail=f"파일 파싱 실패: {safe_filename} - {str(e)}"
                    )

            logger.info(f"Analyzing {len(texts)} documents for case {case_id}")
            analysis = await case_analyzer.analyze_documents(texts, filenames)

            scenario_info = scenario_detector.detect_scenario(analysis, filenames)
            logger.info(f"Detected scenario: {scenario_info['scenario_name']} (confidence: {scenario_info['confidence']})")

            response_dict = {
                "case_id": case_id,
                "summary": analysis.get('summary', ''),
                "document_types": analysis.get('document_types', []),
                "issues": analysis.get('issues', []),
                "key_dates": analysis.get('key_dates', {}),
                "parties": analysis.get('parties', {}),
                "related_cases": analysis.get('related_cases', []),
                "suggested_case_name": analysis.get('suggested_case_name', f"사건_{case_id[:8]}"),
                "suggested_next_steps": analysis.get('suggested_next_steps', []),
                "uploaded_files": [{"filename": f["filename"], "size": f["size"]} for f in file_info],
                "scenario": scenario_info
            }

            response = CaseAnalysisResponse(**response_dict)

            analysis_path = case_dir / "analysis.json"
            with open(analysis_path, "w", encoding="utf-8") as f:
                json.dump(response_dict, f, ensure_ascii=False, indent=2)

            logger.info(f"Case analysis completed: {case_id}")
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Case upload error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def validate_case_id(case_id: str) -> str:
        """
        Case ID 검증 (UUID 형식)

        경로 탐색 공격 방지
        """
        # UUID 형식 검증
        try:
            uuid_obj = uuid.UUID(case_id)
            validated_id = str(uuid_obj)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid case ID format"
            )

        # 추가 보안 검증
        if '..' in case_id or '/' in case_id or '\\' in case_id:
            logger.warning(f"Path traversal attempt in case_id: {case_id}")
            raise HTTPException(
                status_code=400,
                detail="Invalid case ID"
            )

        return validated_id

    @router.get("/{case_id}")
    async def get_case_analysis(case_id: str):
        """저장된 사건 분석 결과 조회"""
        try:
            # Case ID 검증
            validated_id = validate_case_id(case_id)

            case_dir = upload_dir / validated_id
            analysis_path = case_dir / "analysis.json"

            # 경로 정규화 및 검증
            resolved_path = analysis_path.resolve()
            if not str(resolved_path).startswith(str(upload_dir.resolve())):
                logger.error(f"Path traversal attempt: {resolved_path}")
                raise HTTPException(status_code=400, detail="Invalid path")

            if not analysis_path.exists():
                raise HTTPException(status_code=404, detail="Case not found")

            with open(analysis_path, "r", encoding="utf-8") as f:
                analysis = json.load(f)

            return analysis

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get case error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/{case_id}")
    async def delete_case(case_id: str):
        """사건 삭제"""
        try:
            # Case ID 검증
            validated_id = validate_case_id(case_id)

            case_dir = upload_dir / validated_id

            # 경로 정규화 및 검증
            resolved_dir = case_dir.resolve()
            if not str(resolved_dir).startswith(str(upload_dir.resolve())):
                logger.error(f"Path traversal attempt: {resolved_dir}")
                raise HTTPException(status_code=400, detail="Invalid path")

            if not case_dir.exists():
                raise HTTPException(status_code=404, detail="Case not found")

            shutil.rmtree(case_dir)

            logger.info(f"Case deleted: {validated_id}")
            return {"success": True, "message": f"Case {validated_id} deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Delete case error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("")
    async def list_cases():
        """모든 사건 목록 조회"""
        try:
            cases = []

            for case_dir in upload_dir.iterdir():
                if case_dir.is_dir():
                    analysis_path = case_dir / "analysis.json"
                    if analysis_path.exists():
                        with open(analysis_path, "r", encoding="utf-8") as f:
                            analysis = json.load(f)
                        cases.append({
                            "case_id": case_dir.name,
                            "case_name": analysis.get("suggested_case_name", "Unknown"),
                            "summary": analysis.get("summary", "")[:200],
                            "document_count": len(analysis.get("uploaded_files", [])),
                            "created_at": analysis_path.stat().st_ctime
                        })

            cases.sort(key=lambda x: x["created_at"], reverse=True)

            return {"cases": cases, "total": len(cases)}

        except Exception as e:
            logger.error(f"List cases error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
