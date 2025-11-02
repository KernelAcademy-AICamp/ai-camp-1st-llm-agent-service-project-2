"""
LawLaw Backend Server
FastAPI 기반 백엔드 서버 - Ollama를 통한 로컬 LLM 연동
RAG + Constitutional AI 통합
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import json
import logging
from datetime import datetime
import sys
from pathlib import Path
import uuid
import shutil
import asyncio

# 프로젝트 루트 경로를 Python path에 추가
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# 로컬 모듈 임포트
from app.backend.core.llm.llm_client import create_llm_client
from app.backend.core.embeddings.embedder import KoreanLegalEmbedder
from app.backend.core.embeddings.vectordb import ChromaVectorDB
from app.backend.core.retrieval.retriever import LegalDocumentRetriever
from app.backend.core.retrieval.bm25_index import BM25Index
from app.backend.core.retrieval.hybrid_retriever import HybridRetriever
from app.backend.core.llm.constitutional_chatbot import ConstitutionalLawChatbot
from app.backend.core.llm.adapter_chatbot import AdapterChatbot
from app.backend.services.file_parser import FileParser
from app.backend.services.case_analyzer import CaseAnalyzer
from app.backend.services.scenario_detector import ScenarioDetector
from app.backend.services.document_generator import DocumentGenerator
from configs.config import config

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="LawLaw Backend API",
    description="형사법 전문 AI 어시스턴트 백엔드 API",
    version="0.1.0"
)

# CORS 설정 (Electron 앱과의 통신을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "file://"],  # Electron과 React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RAG 시스템 초기화
embedder = None
vectordb = None
bm25_index = None
hybrid_retriever = None
constitutional_chatbot = None

try:
    # 임베딩 모델 초기화
    embedder = KoreanLegalEmbedder()
    logger.info("Embedder initialized successfully")

    # 벡터 DB 초기화 (기존 데이터 로드)
    vectordb = ChromaVectorDB(
        persist_directory=str(BASE_DIR / "data" / "vectordb" / "chroma"),
        collection_name="criminal_law_docs"
    )
    logger.info(f"Vector DB loaded with {vectordb.get_count()} documents")

    # BM25 인덱스 초기화
    bm25_index_path = BASE_DIR / "data" / "vectordb" / "bm25"
    if bm25_index_path.exists():
        bm25_index = BM25Index()
        bm25_index.load(str(bm25_index_path / "bm25_index.pkl"))
        logger.info(f"BM25 index loaded with {bm25_index.get_count()} documents")

    # Semantic Retriever 초기화
    semantic_retriever = LegalDocumentRetriever(embedder=embedder, vectordb=vectordb)

    # Hybrid Retriever 초기화 (Semantic + BM25)
    if bm25_index:
        hybrid_retriever = HybridRetriever(
            semantic_retriever=semantic_retriever,
            bm25_index=bm25_index,
            fusion_method='rrf',
            semantic_weight=0.5,
            enable_adaptive_weighting=True
        )
        logger.info("Hybrid Retriever initialized successfully")
    else:
        hybrid_retriever = semantic_retriever
        logger.info("Using Semantic Retriever only (BM25 index not found)")

except Exception as e:
    logger.error(f"Failed to initialize RAG system: {e}")
    logger.info("Will use fallback mode without RAG")

# LLM 클라이언트 초기화 (OpenAI 사용)
llm_client = None
OPENAI_API_KEY = config.llm.openai_api_key
MODEL_NAME = "gpt-4-turbo-preview"

try:
    llm_client = create_llm_client(
        provider="openai",
        api_key=OPENAI_API_KEY,
        model=MODEL_NAME,
        temperature=0.1,  # 법률 답변은 낮은 temperature
        max_tokens=2000
    )
    logger.info(f"OpenAI LLM client initialized successfully (model={MODEL_NAME})")

    # Constitutional AI 챗봇 초기화 (Adapter 지원)
    if hybrid_retriever and llm_client:
        constitutional_chatbot = AdapterChatbot(
            retriever=hybrid_retriever,
            llm_client=llm_client,
            enable_self_critique=True,  # Self-Critique 활성화
            critique_threshold=0.5
        )
        logger.info("Adapter-enabled Constitutional AI Chatbot initialized successfully")

except Exception as e:
    logger.warning(f"Failed to initialize Ollama client: {e}")
    logger.info("API will run without LLM support")

# Request/Response 모델
class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None
    temperature: Optional[float] = 0.7

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    model: str

class SearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 10

class SearchResult(BaseModel):
    id: str
    title: str
    type: str
    summary: str
    date: str
    relevance: float
    citation: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    model_status: str
    timestamp: str

@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "name": "LawLaw Backend API",
        "version": "0.1.0",
        "status": "running"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """서버 및 모델 상태 확인"""
    try:
        # OpenAI API 키 및 LLM 클라이언트 상태 확인
        if llm_client and OPENAI_API_KEY:
            model_available = True
        else:
            model_available = False

        return HealthResponse(
            status="healthy" if model_available else "degraded",
            model_status="available" if model_available else "not_configured",
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            model_status="error",
            timestamp=datetime.now().isoformat()
        )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Constitutional AI 기반 법률 챗봇"""
    if constitutional_chatbot:
        # Constitutional AI 챗봇 사용 (RAG + Self-Critique)
        try:
            result = constitutional_chatbot.chat(
                query=request.message,
                top_k=5,
                include_critique_log=False
            )

            # 출처 정보 포함한 응답 구성
            response_text = result['answer']
            if result.get('sources'):
                response_text += "\n\n📚 참고 자료:\n"
                for i, source in enumerate(result['sources'][:3], 1):
                    metadata = source.get('metadata', {})
                    response_text += f"{i}. {metadata.get('source', 'Unknown')} - {metadata.get('date', '')}\n"

            return ChatResponse(
                response=response_text,
                timestamp=datetime.now().isoformat(),
                model="GPT-4 + Constitutional AI + RAG"
            )

        except Exception as e:
            logger.error(f"Constitutional AI chat error: {e}")
            # Fallback to simple LLM
            if llm_client:
                response_text = llm_client.generate(
                    prompt=request.message,
                    temperature=request.temperature
                )
                return ChatResponse(
                    response=response_text,
                    timestamp=datetime.now().isoformat(),
                    model="GPT-4"
                )
            raise HTTPException(status_code=500, detail=str(e))

    elif llm_client:
        # RAG 없이 LLM만 사용 (Fallback)
        try:
            response_text = llm_client.generate(
                prompt=request.message,
                temperature=request.temperature
            )

            return ChatResponse(
                response=response_text,
                timestamp=datetime.now().isoformat(),
                model="GPT-4"
            )

        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    else:
        raise HTTPException(status_code=503, detail="Chat service not available")

@app.post("/search", response_model=List[SearchResult])
async def search_legal_documents(request: SearchRequest):
    """Hybrid Search 기반 법률 문서 검색"""
    if hybrid_retriever:
        try:
            # Hybrid Search 실행 (Semantic + BM25)
            results = hybrid_retriever.retrieve(
                query=request.query,
                top_k=request.limit or 10,
                filter_metadata=request.filters
            )

            # 검색 결과를 API 응답 형식으로 변환
            search_results = []
            for i, result in enumerate(results):
                metadata = result.get('metadata', {})

                # 문서 타입 결정
                doc_type = metadata.get('type', 'unknown')
                if '판례' in metadata.get('source', ''):
                    doc_type = 'case'
                elif '법령' in metadata.get('source', ''):
                    doc_type = 'law'
                elif '해석례' in metadata.get('source', ''):
                    doc_type = 'interpretation'

                search_results.append(SearchResult(
                    id=str(i + 1),
                    title=metadata.get('title', f"문서 {i + 1}"),
                    type=doc_type,
                    summary=result.get('text', '')[:200],  # 요약은 처음 200자
                    date=metadata.get('date', ''),
                    relevance=min(100, int(result.get('score', 0) * 100)),  # 점수를 백분율로
                    citation=metadata.get('citation', metadata.get('source', ''))
                ))

            logger.info(f"Search returned {len(search_results)} results for query: {request.query}")
            return search_results

        except Exception as e:
            logger.error(f"Search error: {e}")
            # Fallback to mock data
            return _get_mock_search_results(request.query, request.limit)

    else:
        # RAG 시스템이 없을 때 Mock 데이터 반환
        return _get_mock_search_results(request.query, request.limit)

def _get_mock_search_results(query: str, limit: int) -> List[SearchResult]:
    """Mock 검색 결과 (Fallback)"""
    mock_results = [
        SearchResult(
            id="1",
            title="대법원 2023도1234 판결",
            type="case",
            summary="위법수집증거의 증거능력에 관한 판단 기준을 제시한 사례",
            date="2023-12-15",
            relevance=95.0,
            citation="대법원 2023. 12. 15. 선고 2023도1234 판결"
        ),
        SearchResult(
            id="2",
            title="형사소송법 제308조의2",
            type="law",
            summary="위법수집증거의 배제 - 적법한 절차에 따르지 아니하고 수집한 증거는 증거로 할 수 없다",
            date="2007-06-01",
            relevance=90.0,
            citation="형사소송법 제308조의2"
        )
    ]
    return mock_results[:limit]

class AnalyzeRequest(BaseModel):
    content: str
    document_type: Optional[str] = None

class AnalyzeResponse(BaseModel):
    analysis: str
    sources: List[Dict[str, Any]]
    timestamp: str

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_document(request: AnalyzeRequest):
    """법률 문서 분석 (Constitutional AI 적용)"""
    if constitutional_chatbot:
        try:
            # Constitutional AI 챗봇으로 문서 분석
            analysis_query = f"""다음 법률 문서를 분석하여 주요 내용을 요약하고 법적 쟁점을 파악해주세요:

{request.content}

분석 형식:
1. 문서 요약
2. 주요 법적 쟁점
3. 관련 법령 및 판례
4. 실무적 시사점"""

            result = constitutional_chatbot.chat(
                query=analysis_query,
                top_k=5,
                include_critique_log=False
            )

            return AnalyzeResponse(
                analysis=result['answer'],
                sources=result.get('sources', []),
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Constitutional AI analysis error: {e}")
            # Fallback to simple LLM
            if llm_client:
                analysis_text = llm_client.generate(
                    prompt=analysis_query,
                    temperature=0.1
                )
                return AnalyzeResponse(
                    analysis=analysis_text,
                    sources=[],
                    timestamp=datetime.now().isoformat()
                )
            raise HTTPException(status_code=500, detail=str(e))

    elif llm_client:
        # RAG 없이 LLM만 사용 (Fallback)
        try:
            prompt = f"""다음 법률 문서를 분석하여 주요 내용을 요약하고 법적 쟁점을 파악해주세요:

{request.content}

분석 형식:
1. 문서 요약
2. 주요 법적 쟁점
3. 관련 법령 및 판례
4. 실무적 시사점"""

            analysis_text = llm_client.generate(
                prompt=prompt,
                temperature=0.1
            )

            return AnalyzeResponse(
                analysis=analysis_text,
                sources=[],
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Document analysis error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    else:
        raise HTTPException(status_code=503, detail="Analysis service not available")

# ============================================
# File Upload & Case Management Endpoints
# ============================================

# 업로드된 파일 임시 저장 디렉토리
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# CaseAnalyzer 초기화
case_analyzer = None
if llm_client:
    case_analyzer = CaseAnalyzer(llm_client=llm_client, retriever=hybrid_retriever)
    logger.info("CaseAnalyzer initialized successfully")

# DocumentGenerator 초기화
document_generator = None
if llm_client:
    document_generator = DocumentGenerator(llm_client=llm_client)
    logger.info("DocumentGenerator initialized successfully")

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
    uploaded_files: List[Dict[str, str]]
    scenario: Dict[str, Any]  # 시나리오 정보

@app.post("/cases/upload")
async def upload_case_files(files: List[UploadFile] = File(...)):
    """
    사건 파일 업로드 및 분석

    Args:
        files: 업로드할 파일 리스트 (PDF, DOCX, TXT)

    Returns:
        {
            "case_id": "uuid",
            "summary": "사건 요약",
            "document_types": ["판결문", "계약서"],
            "issues": ["쟁점1", "쟁점2"],
            "key_dates": {"선고일": "2024-01-15"},
            "parties": {"원고": "홍길동", "피고": "김철수"},
            "related_cases": [...],
            "suggested_case_name": "AI 제안 사건명",
            "suggested_next_steps": ["다음 단계 제안"],
            "uploaded_files": [{"filename": "file.pdf", "size": 1024}]
        }
    """
    if not case_analyzer:
        raise HTTPException(status_code=503, detail="Case analyzer not available")

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    try:
        # 사건 ID 생성
        case_id = str(uuid.uuid4())
        case_dir = UPLOAD_DIR / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        # 파일 저장 및 텍스트 추출
        texts = []
        filenames = []
        file_info = []

        for file in files:
            # 파일 확장자 확인
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in ['.pdf', '.docx', '.doc', '.txt']:
                raise HTTPException(
                    status_code=400,
                    detail=f"지원하지 않는 파일 형식: {file.filename} (지원: PDF, DOCX, TXT)"
                )

            # 파일 저장
            file_path = case_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            # 파일 정보 저장
            file_info.append({
                "filename": file.filename,
                "size": len(content),
                "path": str(file_path)
            })

            # 텍스트 추출
            try:
                text = FileParser.parse_file(str(file_path))
                texts.append(text)
                filenames.append(file.filename)
                logger.info(f"Successfully parsed {file.filename}: {len(text)} characters")
            except Exception as e:
                logger.error(f"Failed to parse {file.filename}: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"파일 파싱 실패: {file.filename} - {str(e)}"
                )

        # AI 분석 실행
        logger.info(f"Analyzing {len(texts)} documents for case {case_id}")
        analysis = await case_analyzer.analyze_documents(texts, filenames)

        # 시나리오 자동 감지
        scenario_info = ScenarioDetector.detect_scenario(analysis, filenames)
        logger.info(f"Detected scenario: {scenario_info['scenario_name']} (confidence: {scenario_info['confidence']})")

        # 응답 구성
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
            "scenario": scenario_info  # 시나리오 정보 추가
        }

        response = CaseAnalysisResponse(**response_dict)

        # 분석 결과를 JSON으로 저장
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

@app.get("/cases/{case_id}")
async def get_case_analysis(case_id: str):
    """
    저장된 사건 분석 결과 조회

    Args:
        case_id: 사건 ID

    Returns:
        저장된 사건 분석 결과
    """
    try:
        case_dir = UPLOAD_DIR / case_id
        analysis_path = case_dir / "analysis.json"

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

@app.delete("/cases/{case_id}")
async def delete_case(case_id: str):
    """
    사건 삭제

    Args:
        case_id: 사건 ID

    Returns:
        삭제 결과
    """
    try:
        case_dir = UPLOAD_DIR / case_id

        if not case_dir.exists():
            raise HTTPException(status_code=404, detail="Case not found")

        # 디렉토리 삭제
        shutil.rmtree(case_dir)

        logger.info(f"Case deleted: {case_id}")
        return {"success": True, "message": f"Case {case_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete case error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cases")
async def list_cases():
    """
    모든 사건 목록 조회

    Returns:
        사건 목록
    """
    try:
        cases = []

        for case_dir in UPLOAD_DIR.iterdir():
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

        # 생성 시간 역순으로 정렬
        cases.sort(key=lambda x: x["created_at"], reverse=True)

        return {"cases": cases, "total": len(cases)}

    except Exception as e:
        logger.error(f"List cases error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# Template & Document Generation Endpoints
# ============================================

class DocumentGenerationRequest(BaseModel):
    case_id: str
    template_name: str
    generation_mode: Optional[str] = "quick"  # "quick" or "custom"
    custom_fields: Optional[Dict[str, str]] = None
    user_instructions: Optional[str] = None

class DocumentGenerationResponse(BaseModel):
    document_id: str
    title: str
    content: str
    template_used: str
    metadata: Dict[str, Any]

@app.post("/documents/generate", response_model=DocumentGenerationResponse)
async def generate_document(request: DocumentGenerationRequest):
    """
    템플릿 기반 법률 문서 생성

    Args:
        case_id: 사건 ID
        template_name: 템플릿 이름 (예: "소장", "답변서", "고소장")
        user_instructions: 사용자 추가 지시사항 (선택)

    Returns:
        생성된 문서 정보
    """
    if not document_generator:
        raise HTTPException(status_code=503, detail="Document generator not available")

    try:
        # 사건 분석 결과 로드
        case_dir = UPLOAD_DIR / request.case_id
        analysis_path = case_dir / "analysis.json"

        if not analysis_path.exists():
            raise HTTPException(status_code=404, detail="Case not found")

        with open(analysis_path, "r", encoding="utf-8") as f:
            case_analysis = json.load(f)

        # 문서 생성
        logger.info(f"Generating document '{request.template_name}' for case {request.case_id} (mode: {request.generation_mode})")
        document = await document_generator.generate_document(
            template_name=request.template_name,
            case_analysis=case_analysis,
            generation_mode=request.generation_mode,
            custom_fields=request.custom_fields,
            user_instructions=request.user_instructions
        )

        # 문서 ID 생성 및 저장
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

@app.get("/documents/{case_id}/{document_id}")
async def get_generated_document(case_id: str, document_id: str):
    """
    생성된 문서 조회

    Args:
        case_id: 사건 ID
        document_id: 문서 ID

    Returns:
        생성된 문서 정보
    """
    try:
        document_path = UPLOAD_DIR / case_id / "documents" / f"{document_id}.json"

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

@app.get("/documents/{case_id}")
async def list_generated_documents(case_id: str):
    """
    사건의 모든 생성 문서 목록 조회

    Args:
        case_id: 사건 ID

    Returns:
        생성된 문서 목록
    """
    try:
        documents_dir = UPLOAD_DIR / case_id / "documents"

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

        # 생성 시간 역순 정렬
        documents.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {"documents": documents, "total": len(documents)}

    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{case_id}/{document_id}")
async def delete_generated_document(case_id: str, document_id: str):
    """
    생성된 문서 삭제

    Args:
        case_id: 사건 ID
        document_id: 문서 ID

    Returns:
        삭제 결과
    """
    try:
        document_path = UPLOAD_DIR / case_id / "documents" / f"{document_id}.json"

        if not document_path.exists():
            raise HTTPException(status_code=404, detail="Document not found")

        document_path.unlink()

        logger.info(f"Document deleted: {document_id}")
        return {"success": True, "message": f"Document {document_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scenarios")
async def list_scenarios():
    """
    사용 가능한 시나리오 및 템플릿 목록 조회

    Returns:
        시나리오 및 템플릿 목록
    """
    return {"scenarios": ScenarioDetector.SCENARIOS}

# ============================================
# Adapter Management Endpoints (QDoRA)
# ============================================

class AdapterLoadRequest(BaseModel):
    adapter_name: str

class AdapterInfoResponse(BaseModel):
    current_adapter: Optional[str]
    is_adapter_loaded: bool
    available_adapters: List[str]
    metrics: Dict[str, Any]

@app.post("/adapter/load")
async def load_adapter(request: AdapterLoadRequest):
    """
    QDoRA Adapter 로드

    Args:
        adapter_name: Adapter 이름 (예: "traffic", "criminal")

    Returns:
        {
            "success": bool,
            "message": str,
            "current_adapter": str
        }
    """
    if not constitutional_chatbot:
        raise HTTPException(status_code=503, detail="Chatbot not available")

    if not isinstance(constitutional_chatbot, AdapterChatbot):
        raise HTTPException(status_code=400, detail="Adapter feature not supported")

    try:
        success = constitutional_chatbot.load_adapter(request.adapter_name)

        if success:
            return {
                "success": True,
                "message": f"Adapter '{request.adapter_name}' loaded successfully",
                "current_adapter": request.adapter_name
            }
        else:
            return {
                "success": False,
                "message": f"Failed to load adapter '{request.adapter_name}'. Check if it exists in Ollama.",
                "current_adapter": None
            }

    except Exception as e:
        logger.error(f"Adapter load error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/adapter/unload")
async def unload_adapter():
    """Adapter 언로드 (Base Model로 복귀)"""
    if not constitutional_chatbot:
        raise HTTPException(status_code=503, detail="Chatbot not available")

    if not isinstance(constitutional_chatbot, AdapterChatbot):
        raise HTTPException(status_code=400, detail="Adapter feature not supported")

    try:
        constitutional_chatbot.unload_adapter()

        return {
            "success": True,
            "message": "Adapter unloaded, returned to base model",
            "current_adapter": None
        }

    except Exception as e:
        logger.error(f"Adapter unload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/adapter/list")
async def list_adapters():
    """사용 가능한 Adapter 목록 조회"""
    if not constitutional_chatbot:
        raise HTTPException(status_code=503, detail="Chatbot not available")

    if not isinstance(constitutional_chatbot, AdapterChatbot):
        return []

    try:
        adapters = constitutional_chatbot.list_available_adapters()
        return adapters

    except Exception as e:
        logger.error(f"List adapters error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/adapter/info", response_model=AdapterInfoResponse)
async def get_adapter_info():
    """현재 Adapter 정보 및 메트릭 조회"""
    if not constitutional_chatbot:
        raise HTTPException(status_code=503, detail="Chatbot not available")

    if not isinstance(constitutional_chatbot, AdapterChatbot):
        return AdapterInfoResponse(
            current_adapter=None,
            is_adapter_loaded=False,
            available_adapters=[],
            metrics={}
        )

    try:
        info = constitutional_chatbot.get_adapter_info()
        return AdapterInfoResponse(**info)

    except Exception as e:
        logger.error(f"Get adapter info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)