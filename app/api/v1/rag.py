"""
RAG (Retrieval-Augmented Generation) API

ChromaDB를 사용한 유사 판례 검색 및 법률 질의응답
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import chromadb
from chromadb.config import Settings
from openai import OpenAI
import os

router = APIRouter(prefix="/rag", tags=["RAG"])

# ChromaDB 클라이언트 초기화
chroma_client = chromadb.PersistentClient(
    path=os.getenv("CHROMA_DB_PATH", "./chroma_db"),
    settings=Settings(anonymized_telemetry=False)
)

# OpenAI 클라이언트 초기화
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 컬렉션
COLLECTION_NAME = "traffic_legal_cases"


# === Request/Response 모델 ===

class SimilarCaseRequest(BaseModel):
    """유사 판례 검색 요청"""
    query: str = Field(..., description="검색 쿼리", min_length=1)
    top_k: int = Field(5, description="반환할 결과 수", ge=1, le=20)
    case_type: Optional[str] = Field(None, description="케이스 타입 필터 (판례, 결정례, 해석례, 법령)")
    court_name: Optional[str] = Field(None, description="법원명 필터")


class SimilarCaseResult(BaseModel):
    """유사 판례 검색 결과"""
    case_id: str
    case_type: str
    사건번호: str
    법원명: str
    선고일자: str
    판결요지: str
    similarity_score: float
    full_document: Optional[str] = None


class SimilarCaseResponse(BaseModel):
    """유사 판례 검색 응답"""
    query: str
    results: List[SimilarCaseResult]
    total_found: int


class LegalQARequest(BaseModel):
    """법률 질의응답 요청"""
    question: str = Field(..., description="법률 질문", min_length=1)
    top_k: int = Field(3, description="참조할 판례 수", ge=1, le=10)
    include_sources: bool = Field(True, description="출처 판례 포함 여부")


class LegalQAResponse(BaseModel):
    """법률 질의응답 응답"""
    question: str
    answer: str
    sources: Optional[List[SimilarCaseResult]] = None


class RecommendCaseRequest(BaseModel):
    """판례 추천 요청"""
    case_id: str = Field(..., description="기준 판례 ID")
    top_k: int = Field(5, description="추천할 판례 수", ge=1, le=20)


# === Helper Functions ===

def get_collection():
    """ChromaDB 컬렉션 가져오기"""
    try:
        return chroma_client.get_collection(COLLECTION_NAME)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ChromaDB 컬렉션을 찾을 수 없습니다: {str(e)}"
        )


def create_embedding(text: str) -> List[float]:
    """OpenAI API로 임베딩 생성"""
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000]
        )
        return response.data[0].embedding
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"임베딩 생성 실패: {str(e)}"
        )


def build_where_filter(case_type: Optional[str], court_name: Optional[str]) -> Optional[dict]:
    """ChromaDB 필터 조건 생성"""
    conditions = []

    if case_type:
        conditions.append({"case_type": case_type})

    if court_name:
        conditions.append({"법원명": court_name})

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}


# === API Endpoints ===

@router.post("/similar-cases", response_model=SimilarCaseResponse)
async def find_similar_cases(request: SimilarCaseRequest):
    """
    유사 판례 검색

    주어진 쿼리와 의미적으로 유사한 판례를 검색합니다.
    """
    collection = get_collection()

    # 쿼리 임베딩 생성
    query_embedding = create_embedding(request.query)

    # 필터 조건 생성
    where_filter = build_where_filter(request.case_type, request.court_name)

    # ChromaDB 검색
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.top_k,
            where=where_filter,
            include=["metadatas", "documents", "distances"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"검색 실패: {str(e)}"
        )

    # 결과 변환
    similar_cases = []
    for i, (metadata, document, distance) in enumerate(zip(
        results['metadatas'][0],
        results['documents'][0],
        results['distances'][0]
    )):
        similar_cases.append(SimilarCaseResult(
            case_id=results['ids'][0][i],
            case_type=metadata.get('case_type', ''),
            사건번호=metadata.get('사건번호', ''),
            법원명=metadata.get('법원명', ''),
            선고일자=metadata.get('선고일자', ''),
            판결요지=metadata.get('판결요지', ''),
            similarity_score=1.0 - distance,  # distance를 similarity로 변환
            full_document=document if request.top_k <= 5 else None
        ))

    return SimilarCaseResponse(
        query=request.query,
        results=similar_cases,
        total_found=len(similar_cases)
    )


@router.post("/legal-qa", response_model=LegalQAResponse)
async def legal_qa(request: LegalQARequest):
    """
    법률 질의응답 (RAG)

    유사 판례를 검색하고 GPT를 활용하여 법률 질문에 답변합니다.
    """
    collection = get_collection()

    # 1. 유사 판례 검색
    query_embedding = create_embedding(request.question)

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.top_k,
            include=["metadatas", "documents", "distances"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"판례 검색 실패: {str(e)}"
        )

    # 2. 컨텍스트 생성
    context_parts = []
    sources = []

    for i, (metadata, document, distance) in enumerate(zip(
        results['metadatas'][0],
        results['documents'][0],
        results['distances'][0]
    )):
        context_parts.append(f"[판례 {i+1}]\n{document}\n")

        if request.include_sources:
            sources.append(SimilarCaseResult(
                case_id=results['ids'][0][i],
                case_type=metadata.get('case_type', ''),
                사건번호=metadata.get('사건번호', ''),
                법원명=metadata.get('법원명', ''),
                선고일자=metadata.get('선고일자', ''),
                판결요지=metadata.get('판결요지', ''),
                similarity_score=1.0 - distance
            ))

    context = "\n".join(context_parts)

    # 3. GPT 프롬프트 생성
    system_prompt = """당신은 대한민국 교통 관련 법률 전문가입니다.
주어진 판례를 참조하여 사용자의 질문에 정확하고 명확하게 답변하세요.

답변 시 유의사항:
1. 판례의 내용을 근거로 답변하되, 판례 번호를 명시하세요.
2. 법률 용어를 쉽게 설명하세요.
3. 실제 적용 방법을 구체적으로 설명하세요.
4. 불확실한 경우 "판례에 따르면..."과 같이 명확히 표현하세요.
5. 답변은 한국어로 작성하세요.
"""

    user_prompt = f"""다음 판례들을 참조하여 질문에 답변해주세요.

===== 참조 판례 =====
{context}

===== 질문 =====
{request.question}

===== 답변 =====
"""

    # 4. GPT 호출
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # 또는 "gpt-4"
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        answer = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"GPT 호출 실패: {str(e)}"
        )

    return LegalQAResponse(
        question=request.question,
        answer=answer,
        sources=sources if request.include_sources else None
    )


@router.post("/recommend-cases", response_model=SimilarCaseResponse)
async def recommend_cases(request: RecommendCaseRequest):
    """
    판례 추천

    특정 판례와 유사한 다른 판례를 추천합니다.
    """
    collection = get_collection()

    # 1. 기준 판례 조회
    try:
        base_case = collection.get(
            ids=[request.case_id],
            include=["embeddings", "metadatas"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"판례를 찾을 수 없습니다: {str(e)}"
        )

    if not base_case['ids']:
        raise HTTPException(
            status_code=404,
            detail=f"판례를 찾을 수 없습니다: {request.case_id}"
        )

    # 2. 유사 판례 검색 (기준 판례 제외)
    base_embedding = base_case['embeddings'][0]

    try:
        results = collection.query(
            query_embeddings=[base_embedding],
            n_results=request.top_k + 1,  # 기준 판례 포함되므로 +1
            include=["metadatas", "documents", "distances"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"검색 실패: {str(e)}"
        )

    # 3. 결과 변환 (기준 판례 제외)
    similar_cases = []
    for i, (case_id, metadata, document, distance) in enumerate(zip(
        results['ids'][0],
        results['metadatas'][0],
        results['documents'][0],
        results['distances'][0]
    )):
        # 기준 판례는 제외
        if case_id == request.case_id:
            continue

        similar_cases.append(SimilarCaseResult(
            case_id=case_id,
            case_type=metadata.get('case_type', ''),
            사건번호=metadata.get('사건번호', ''),
            법원명=metadata.get('법원명', ''),
            선고일자=metadata.get('선고일자', ''),
            판결요지=metadata.get('판결요지', ''),
            similarity_score=1.0 - distance
        ))

        if len(similar_cases) >= request.top_k:
            break

    base_metadata = base_case['metadatas'][0]
    query_text = f"{base_metadata.get('사건번호', '')} - {base_metadata.get('법원명', '')}"

    return SimilarCaseResponse(
        query=query_text,
        results=similar_cases,
        total_found=len(similar_cases)
    )


@router.get("/stats")
async def get_stats():
    """
    ChromaDB 통계 조회
    """
    try:
        collection = get_collection()
        count = collection.count()

        # 타입별 통계 (샘플링)
        sample = collection.get(
            limit=1000,
            include=["metadatas"]
        )

        type_counts = {}
        for metadata in sample['metadatas']:
            case_type = metadata.get('case_type', '기타')
            type_counts[case_type] = type_counts.get(case_type, 0) + 1

        return {
            "total_cases": count,
            "collection_name": COLLECTION_NAME,
            "type_distribution": type_counts,
            "embedding_model": "text-embedding-3-small",
            "embedding_dimension": 1536
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 실패: {str(e)}"
        )
