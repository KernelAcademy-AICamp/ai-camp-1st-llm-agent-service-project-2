"""
External API Tools Unit Tests

Phase 4 - Week 13: MCP External Tools 테스트

테스트 대상:
- fetch_court_api: 대법원 판례 API 호출
- fetch_statute_api: 법령 API 호출
- parse_legal_document: 법률 문서 파싱
- validate_document_structure: 문서 구조 검증
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from apps.ai_service.mcp.tools.external_tools import (
    fetch_court_api,
    fetch_statute_api,
    parse_legal_document,
    validate_document_structure,
    parse_xml_response,
    element_to_dict,
)


# =============================================================================
# XML Parsing Tests
# =============================================================================

class TestXmlParsing:
    """XML 파싱 유틸리티 테스트"""

    def test_parse_xml_response_simple(self):
        """간단한 XML 파싱"""
        xml_text = "<root><item>테스트</item></root>"
        result = parse_xml_response(xml_text)
        assert "item" in result
        assert result["item"] == "테스트"

    def test_parse_xml_response_nested(self):
        """중첩된 XML 파싱"""
        xml_text = """
        <response>
            <totalCnt>10</totalCnt>
            <prec>
                <사건번호>2020도1234</사건번호>
                <법원명>대법원</법원명>
            </prec>
        </response>
        """
        result = parse_xml_response(xml_text)
        assert result["totalCnt"] == "10"
        assert "prec" in result
        assert result["prec"]["사건번호"] == "2020도1234"

    def test_parse_xml_response_multiple_items(self):
        """여러 항목이 있는 XML 파싱"""
        xml_text = """
        <response>
            <prec><사건번호>2020도1234</사건번호></prec>
            <prec><사건번호>2019도5678</사건번호></prec>
        </response>
        """
        result = parse_xml_response(xml_text)
        assert isinstance(result["prec"], list)
        assert len(result["prec"]) == 2

    def test_parse_xml_response_invalid(self):
        """잘못된 XML 파싱"""
        xml_text = "not valid xml"
        result = parse_xml_response(xml_text)
        assert "error" in result


# =============================================================================
# fetch_court_api Tests
# =============================================================================

class TestFetchCourtApi:
    """대법원 판례 API 테스트"""

    @pytest.mark.asyncio
    async def test_fetch_court_api_no_api_key(self):
        """API 키 없이 호출 시 에러"""
        with patch.dict('os.environ', {'LAW_GO_KR_OC': ''}):
            result = await fetch_court_api(keyword="절도", oc="")
            assert result["success"] is False
            assert "API key" in result["error"]

    @pytest.mark.asyncio
    async def test_fetch_court_api_success(self):
        """성공적인 API 호출"""
        mock_response_text = """
        <PrecSearch>
            <totalCnt>1</totalCnt>
            <prec>
                <판례일련번호>123456</판례일련번호>
                <사건번호>2020도1234</사건번호>
                <사건명>절도죄 판례</사건명>
                <법원명>대법원</법원명>
                <선고일자>20200515</선고일자>
                <사건종류명>형사</사건종류명>
            </prec>
        </PrecSearch>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_response_text

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_court_api(keyword="절도", oc="test_key", fetch_content=False)

            assert result["success"] is True
            assert result["total_count"] == 1
            assert len(result["precedents"]) == 1
            assert result["precedents"][0]["case_number"] == "2020도1234"
            assert result["precedents"][0]["court"] == "대법원"

    @pytest.mark.asyncio
    async def test_fetch_court_api_http_error(self):
        """HTTP 에러 처리"""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_court_api(keyword="절도", oc="test_key")

            assert result["success"] is False
            assert "500" in result["error"]

    @pytest.mark.asyncio
    async def test_fetch_court_api_empty_results(self):
        """검색 결과 없음"""
        mock_response_text = """
        <PrecSearch>
            <totalCnt>0</totalCnt>
        </PrecSearch>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_response_text

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_court_api(keyword="없는검색어", oc="test_key")

            assert result["success"] is True
            assert result["total_count"] == 0
            assert len(result["precedents"]) == 0


# =============================================================================
# fetch_statute_api Tests
# =============================================================================

class TestFetchStatuteApi:
    """법령 API 테스트"""

    @pytest.mark.asyncio
    async def test_fetch_statute_api_no_api_key(self):
        """API 키 없이 호출 시 에러"""
        with patch.dict('os.environ', {'LAW_GO_KR_OC': ''}):
            result = await fetch_statute_api(keyword="형법", oc="")
            assert result["success"] is False
            assert "API key" in result["error"]

    @pytest.mark.asyncio
    async def test_fetch_statute_api_success(self):
        """성공적인 API 호출"""
        mock_response_text = """
        <LawSearch>
            <totalCnt>1</totalCnt>
            <law>
                <법령일련번호>12345</법령일련번호>
                <법령MST>001001</법령MST>
                <법령명한글>형법</법령명한글>
                <공포일자>19530918</공포일자>
                <시행일자>19531001</시행일자>
                <소관부처명>법무부</소관부처명>
                <법령종류>법률</법령종류>
            </law>
        </LawSearch>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_response_text

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_statute_api(keyword="형법", oc="test_key")

            assert result["success"] is True
            assert result["total_count"] == 1
            assert len(result["statutes"]) == 1
            assert result["statutes"][0]["law_name"] == "형법"
            assert result["statutes"][0]["ministry"] == "법무부"

    @pytest.mark.asyncio
    async def test_fetch_statute_api_with_filters(self):
        """필터 적용 테스트"""
        mock_response_text = """
        <LawSearch>
            <totalCnt>0</totalCnt>
        </LawSearch>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_response_text

        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await fetch_statute_api(
                keyword="형법",
                ministry="법무부",
                law_type="법률",
                oc="test_key"
            )

            assert result["success"] is True
            # 호출 파라미터 확인
            call_args = mock_instance.get.call_args
            assert call_args is not None


# =============================================================================
# parse_legal_document Tests
# =============================================================================

class TestParseLegalDocument:
    """법률 문서 파싱 테스트"""

    @pytest.mark.asyncio
    async def test_parse_empty_content(self):
        """빈 내용 파싱"""
        result = await parse_legal_document("")
        assert result["success"] is False
        assert "Empty content" in result["error"]

    @pytest.mark.asyncio
    async def test_parse_precedent_document(self):
        """판례 문서 파싱"""
        content = """
        2020도1234 절도죄 판례

        【판시사항】
        타인의 재물을 절취하는 행위에 대한 판단

        【판결요지】
        절도죄의 성립요건에 관한 판시

        【참조조문】
        형법 제329조
        """

        result = await parse_legal_document(content, doc_type="precedent")

        assert result["success"] is True
        assert result["doc_type"] == "precedent"
        assert len(result["sections"]) >= 2
        section_names = [s["name"] for s in result["sections"]]
        assert "판시사항" in section_names
        assert "판결요지" in section_names

    @pytest.mark.asyncio
    async def test_parse_statute_document(self):
        """법령 문서 파싱"""
        content = """
        형법

        제1조(목적) 이 법은 범죄와 형벌에 관한 사항을 규정함을 목적으로 한다.

        제2조(국내범) 본법은 대한민국 영역 내에서 죄를 범한 내국인과 외국인에게 적용한다.

        제3조(내국인의 국외범) 본법은 대한민국 영역 외에서 죄를 범한 내국인에게 적용한다.
        """

        result = await parse_legal_document(content, doc_type="statute")

        assert result["success"] is True
        assert result["doc_type"] == "statute"
        assert len(result["sections"]) >= 3
        section_names = [s["name"] for s in result["sections"]]
        assert any("제1조" in name for name in section_names)

    @pytest.mark.asyncio
    async def test_parse_unknown_document(self):
        """일반 문서 파싱"""
        content = """
        계약서 제목

        계약 내용 첫 번째 단락입니다.

        계약 내용 두 번째 단락입니다.

        서명 및 날짜
        """

        result = await parse_legal_document(content, doc_type="unknown")

        assert result["success"] is True
        assert len(result["sections"]) >= 1

    @pytest.mark.asyncio
    async def test_parse_html_content(self):
        """HTML 포함 문서 파싱"""
        content = """
        <html>
        <body>
        <h1>판례 제목</h1>
        <p>【판시사항】</p>
        <p>내용입니다.</p>
        </body>
        </html>
        """

        result = await parse_legal_document(content, doc_type="precedent")

        assert result["success"] is True
        # HTML이 제거되어 파싱됨


# =============================================================================
# validate_document_structure Tests
# =============================================================================

class TestValidateDocumentStructure:
    """문서 구조 검증 테스트"""

    @pytest.mark.asyncio
    async def test_validate_valid_precedent(self):
        """유효한 판례 문서 검증"""
        data = {
            "case_number": "2020도1234",
            "title": "절도죄 판례",
            "content": "판례 내용입니다. 이 판례는 절도죄의 성립요건에 관한 것입니다.",
            "court": "대법원",
            "decision_date": "2020-05-15"
        }

        result = await validate_document_structure(data, doc_type="precedent")

        assert result["valid"] is True
        assert len(result["missing_fields"]) == 0

    @pytest.mark.asyncio
    async def test_validate_invalid_precedent(self):
        """필수 필드 누락 판례 검증"""
        data = {
            "title": "절도죄 판례"
            # case_number, content 누락
        }

        result = await validate_document_structure(data, doc_type="precedent")

        assert result["valid"] is False
        assert "case_number" in result["missing_fields"]
        assert "content" in result["missing_fields"]

    @pytest.mark.asyncio
    async def test_validate_statute(self):
        """법령 문서 검증"""
        data = {
            "law_name": "형법",
            "content": "법령 내용입니다. 제1조 목적 이 법은 범죄와 형벌에 관한 사항을 규정한다.",
            "law_type": "법률",
            "ministry": "법무부"
        }

        result = await validate_document_structure(data, doc_type="statute")

        assert result["valid"] is True
        assert len(result["missing_fields"]) == 0

    @pytest.mark.asyncio
    async def test_validate_contract(self):
        """계약서 문서 검증"""
        data = {
            "title": "용역 계약서",
            "content": "계약서 내용입니다. 충분히 긴 내용을 포함합니다.",
            "parties": ["갑", "을"]
        }

        result = await validate_document_structure(data, doc_type="contract")

        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_short_content_warning(self):
        """짧은 내용 경고"""
        data = {
            "case_number": "2020도1234",
            "title": "판례",
            "content": "짧음"  # 50자 미만
        }

        result = await validate_document_structure(data, doc_type="precedent")

        assert result["valid"] is True
        assert any("short" in w.lower() for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_validate_missing_recommended_fields(self):
        """권장 필드 누락 경고"""
        data = {
            "case_number": "2020도1234",
            "title": "판례",
            "content": "판례 내용입니다. 이 판례는 충분히 긴 내용을 가지고 있습니다."
            # court, decision_date 등 권장 필드 누락
        }

        result = await validate_document_structure(data, doc_type="precedent")

        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("recommended" in w.lower() for w in result["warnings"])


# =============================================================================
# Integration Tests
# =============================================================================

class TestExternalToolsIntegration:
    """External Tools 통합 테스트"""

    @pytest.mark.asyncio
    async def test_parse_and_validate_flow(self):
        """파싱 후 검증 워크플로우"""
        # 1. 문서 파싱
        content = """
        2020도1234 절도죄 판례

        【판시사항】
        타인의 재물을 절취하는 행위

        【판결요지】
        절도죄의 성립요건
        """

        parse_result = await parse_legal_document(content, doc_type="precedent")
        assert parse_result["success"] is True

        # 2. 파싱 결과를 기반으로 검증 데이터 구성
        validation_data = {
            "case_number": "2020도1234",
            "title": parse_result.get("title", ""),
            "content": content,
            "sections": parse_result["sections"]
        }

        # 3. 문서 구조 검증
        validate_result = await validate_document_structure(validation_data, doc_type="precedent")
        assert validate_result["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
