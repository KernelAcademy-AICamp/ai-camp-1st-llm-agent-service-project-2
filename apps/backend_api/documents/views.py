from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from django.conf import settings
import httpx
import logging

from .models import Document, DocumentChunk, Summary, KeyClause, RiskAnalysisResult, CaseAnalysis
from .serializers import (
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentDetailSerializer,
    DocumentChunkSerializer,
    SummarySerializer,
    KeyClauseSerializer,
    RiskAnalysisResultSerializer,
    CaseAnalysisSerializer,
)

logger = logging.getLogger(__name__)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Document CRUD operations

    Endpoints:
    - POST /api/v1/documents/upload/ - Upload a document
    - GET /api/v1/documents/ - List user's documents
    - GET /api/v1/documents/{id}/ - Retrieve document detail
    - DELETE /api/v1/documents/{id}/ - Delete document
    """

    permission_classes = [IsAuthenticated]
    # parser_classes will be set per action as needed

    def get_queryset(self):
        """
        Return documents for current user only
        """
        return Document.objects.filter(user=self.request.user).select_related('user')

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action
        """
        if self.action == 'upload':
            return DocumentUploadSerializer
        elif self.action == 'retrieve':
            return DocumentDetailSerializer
        return DocumentSerializer

    def list(self, request):
        """
        GET /api/v1/documents/
        List all documents for the current user
        """
        queryset = self.get_queryset()

        # Filter by doc_type if provided
        doc_type = request.query_params.get('doc_type', None)
        if doc_type:
            queryset = queryset.filter(doc_type=doc_type)

        # Filter by status if provided
        doc_status = request.query_params.get('status', None)
        if doc_status:
            queryset = queryset.filter(status=doc_status)

        # Search by title
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
            )

        # Order by created_at (newest first)
        queryset = queryset.order_by('-created_at')

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    def retrieve(self, request, pk=None):
        """
        GET /api/v1/documents/{id}/
        Retrieve a single document with chunks
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(document)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='upload', parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        """
        POST /api/v1/documents/upload/
        Upload a new document

        Request body (multipart/form-data):
        - title: Document title (required)
        - doc_type: Document type (required) - CASE/CONTRACT/STATUTE/PRECEDENT/OTHER
        - language: Language (optional, default: ko)
        - original_file: File to upload (required)

        File validation:
        - Max size: 10MB
        - Allowed extensions: .pdf, .docx, .txt

        Response:
        - 201: Document uploaded successfully
        - 400: Validation error
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            document = serializer.save()

            # Trigger async preprocessing (optional - fire and forget)
            try:
                self._trigger_preprocessing(document)
            except Exception as e:
                logger.warning(f"Failed to trigger preprocessing for document {document.id}: {e}")
                # Don't fail the upload if preprocessing trigger fails

            # Return created document
            response_serializer = DocumentSerializer(document)
            return Response(
                {
                    'message': 'Document uploaded successfully',
                    'document': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                'error': 'Validation failed',
                'details': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, pk=None):
        """
        DELETE /api/v1/documents/{id}/
        Delete a document and its chunks
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete the file from storage
        if document.original_file:
            document.original_file.delete(save=False)

        # Delete the document (chunks will be cascade deleted)
        document.delete()

        return Response(
            {'message': 'Document deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=['get'], url_path='chunks')
    def chunks(self, request, pk=None):
        """
        GET /api/v1/documents/{id}/chunks/
        Get all chunks for a document
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        chunks = document.chunks.all().order_by('chunk_index')
        serializer = DocumentChunkSerializer(chunks, many=True)

        return Response({
            'document_id': str(document.id),
            'document_title': document.title,
            'chunk_count': chunks.count(),
            'chunks': serializer.data
        })

    @action(detail=True, methods=['get'], url_path='summary')
    def summary(self, request, pk=None):
        """
        GET /api/v1/documents/{id}/summary/
        Get summary for a document (most recent GLOBAL summary)
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get the most recent GLOBAL summary
        summary = document.summaries.filter(
            summary_type=Summary.SUMMARY_TYPE_GLOBAL
        ).order_by('-created_at').first()

        if not summary:
            return Response(
                {
                    'document_id': str(document.id),
                    'document_title': document.title,
                    'summary': None,
                    'message': 'No summary available. Call /analyze/ to generate one.'
                },
                status=status.HTTP_200_OK
            )

        serializer = SummarySerializer(summary)
        return Response({
            'document_id': str(document.id),
            'document_title': document.title,
            'summary': serializer.data
        })

    @action(detail=True, methods=['get'], url_path='clauses')
    def clauses(self, request, pk=None):
        """
        GET /api/v1/documents/{id}/clauses/
        Get all key clauses for a document
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get all key clauses, ordered by importance score
        clauses = document.key_clauses.all().order_by('-importance_score', '-created_at')
        serializer = KeyClauseSerializer(clauses, many=True)

        return Response({
            'document_id': str(document.id),
            'document_title': document.title,
            'clause_count': clauses.count(),
            'clauses': serializer.data
        })

    @action(detail=True, methods=['get'], url_path='risk_analysis')
    def risk_analysis(self, request, pk=None):
        """
        GET /api/v1/documents/{id}/risk_analysis/
        Get risk analysis result for a document (most recent)
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get the most recent risk analysis
        risk_analysis = document.risk_analyses.order_by('-created_at').first()

        if not risk_analysis:
            return Response(
                {
                    'document_id': str(document.id),
                    'document_title': document.title,
                    'risk_analysis': None,
                    'message': 'No risk analysis available. Call /analyze_risk/ to generate one.'
                },
                status=status.HTTP_200_OK
            )

        serializer = RiskAnalysisResultSerializer(risk_analysis)
        return Response({
            'document_id': str(document.id),
            'document_title': document.title,
            'risk_analysis': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='analyze_risk')
    def analyze_risk(self, request, pk=None):
        """
        POST /api/v1/documents/{id}/analyze_risk/
        Trigger AI risk analysis for a document

        Request body:
        {
            "llm_model": "gpt-4" | "claude-3-opus" (optional, default from settings)
        }

        Response:
        {
            "success": true,
            "document_id": "...",
            "risk_analysis": {...}
        }
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if document is ready for analysis
        if document.status not in [Document.STATUS_PREPROCESSED, Document.STATUS_EMBEDDED]:
            return Response(
                {
                    'error': 'Document not ready for analysis',
                    'status': document.status,
                    'message': 'Document must be preprocessed first'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get request parameters
        llm_model = request.data.get('llm_model', 'gpt-4')

        result = {
            'success': True,
            'document_id': str(document.id),
            'document_title': document.title
        }

        # Analyze risks
        try:
            risk_obj = self._analyze_risk(document, llm_model)
            result['risk_analysis'] = RiskAnalysisResultSerializer(risk_obj).data
        except Exception as e:
            logger.error(f"Error analyzing risks for document {document.id}: {e}", exc_info=True)
            result['success'] = False
            result['error'] = str(e)

        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='analyze')
    def analyze(self, request, pk=None):
        """
        POST /api/v1/documents/{id}/analyze/
        Trigger AI analysis for a document (summary and/or clause extraction)

        Request body:
        {
            "analysis_type": "summary" | "clauses" | "both" (default: "both"),
            "llm_model": "gpt-4" | "claude-3-opus" (optional, default from settings)
        }

        Response:
        {
            "success": true,
            "document_id": "...",
            "summary": {...} (if requested),
            "clauses": [...] (if requested)
        }
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if document is ready for analysis
        if document.status not in [Document.STATUS_PREPROCESSED, Document.STATUS_EMBEDDED]:
            return Response(
                {
                    'error': 'Document not ready for analysis',
                    'status': document.status,
                    'message': 'Document must be preprocessed first'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get request parameters
        analysis_type = request.data.get('analysis_type', 'both')
        llm_model = request.data.get('llm_model', 'gpt-4')

        if analysis_type not in ['summary', 'clauses', 'both']:
            return Response(
                {'error': 'Invalid analysis_type. Must be: summary, clauses, or both'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = {
            'success': True,
            'document_id': str(document.id),
            'document_title': document.title
        }

        # Generate summary if requested
        if analysis_type in ['summary', 'both']:
            try:
                summary_obj = self._generate_summary(document, llm_model)
                result['summary'] = SummarySerializer(summary_obj).data
            except Exception as e:
                logger.error(f"Error generating summary for document {document.id}: {e}", exc_info=True)
                result['success'] = False
                result['summary_error'] = str(e)

        # Extract clauses if requested
        if analysis_type in ['clauses', 'both']:
            try:
                clause_objs = self._extract_clauses(document, llm_model)
                result['clauses'] = KeyClauseSerializer(clause_objs, many=True).data
                result['clause_count'] = len(clause_objs)
            except Exception as e:
                logger.error(f"Error extracting clauses for document {document.id}: {e}", exc_info=True)
                result['success'] = False
                result['clauses_error'] = str(e)

        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='case-analysis')
    def case_analysis(self, request, pk=None):
        """
        GET /api/v1/documents/{id}/case-analysis/
        Get case analysis for a document (if it exists)
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if document has case analysis
        if not hasattr(document, 'case_analysis'):
            return Response(
                {
                    'document_id': str(document.id),
                    'document_title': document.title,
                    'case_analysis': None,
                    'message': 'No case analysis available. Call /analyze-case/ to generate one.'
                },
                status=status.HTTP_200_OK
            )

        serializer = CaseAnalysisSerializer(document.case_analysis)
        return Response({
            'document_id': str(document.id),
            'document_title': document.title,
            'case_analysis': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='analyze-case')
    def analyze_case(self, request, pk=None):
        """
        POST /api/v1/documents/{id}/analyze-case/
        Trigger AI case analysis for a document

        Request body:
        {
            "llm_model": "gpt-4" | "claude-3-opus" (optional, default from settings),
            "scenario": "소송 준비" | "계약 검토" | "법적 자문" | "기타" (optional)
        }

        Response:
        {
            "success": true,
            "document_id": "...",
            "case_analysis": {...}
        }
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if document is ready for analysis
        if document.status not in [Document.STATUS_PREPROCESSED, Document.STATUS_EMBEDDED]:
            return Response(
                {
                    'error': 'Document not ready for analysis',
                    'status': document.status,
                    'message': 'Document must be preprocessed first'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get request parameters
        llm_model = request.data.get('llm_model', 'gpt-4')
        scenario = request.data.get('scenario', '소송 준비')

        result = {
            'success': True,
            'document_id': str(document.id),
            'document_title': document.title
        }

        # Perform case analysis
        try:
            case_obj = self._analyze_case(document, llm_model, scenario)
            result['case_analysis'] = CaseAnalysisSerializer(case_obj).data
        except Exception as e:
            logger.error(f"Error analyzing case for document {document.id}: {e}", exc_info=True)
            result['success'] = False
            result['error'] = str(e)
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_201_CREATED)

    def _trigger_preprocessing(self, document: Document):
        """
        Trigger document preprocessing via AI Service

        This sends the uploaded file to FastAPI for text extraction and chunking.
        The chunks are then saved to the database.
        """
        if not document.original_file:
            return

        try:
            # Prepare file for upload to AI Service
            file_path = document.original_file.path

            with open(file_path, 'rb') as f:
                files = {'file': (document.original_file.name, f, document.file_type)}
                data = {
                    'chunk_size': 1000,
                    'chunk_overlap': 200
                }

                # Call FastAPI preprocessing endpoint
                ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')
                response = httpx.post(
                    f'{ai_service_url}/preprocess/document',
                    files=files,
                    data=data,
                    timeout=60.0
                )

                if response.status_code == 200:
                    result = response.json()

                    if result.get('success'):
                        # Update document status
                        document.status = Document.STATUS_PREPROCESSED
                        document.save(update_fields=['status'])

                        # Save chunks to database
                        chunks = result.get('chunks', [])
                        chunk_objects = []
                        for chunk_data in chunks:
                            chunk_obj = DocumentChunk.objects.create(
                                document=document,
                                chunk_index=chunk_data['chunk_index'],
                                text=chunk_data['text'],
                                start_offset=chunk_data.get('start_offset'),
                                end_offset=chunk_data.get('end_offset'),
                                token_count=chunk_data.get('token_count')
                            )
                            chunk_objects.append(chunk_obj)

                        logger.info(
                            f"Document {document.id} preprocessed successfully: "
                            f"{len(chunks)} chunks created"
                        )

                        # Trigger indexing after preprocessing
                        try:
                            self._trigger_indexing(document, chunk_objects)
                        except Exception as e:
                            logger.warning(f"Failed to trigger indexing for document {document.id}: {e}")
                            # Don't fail preprocessing if indexing fails
                    else:
                        # Update document status to failed
                        document.status = Document.STATUS_FAILED
                        document.error_message = result.get('error', 'Preprocessing failed')
                        document.save(update_fields=['status', 'error_message'])
                        logger.error(f"Preprocessing failed for document {document.id}: {result.get('error')}")
                else:
                    logger.error(
                        f"AI Service returned error for document {document.id}: "
                        f"{response.status_code} - {response.text}"
                    )
                    document.status = Document.STATUS_FAILED
                    document.error_message = f"AI Service error: {response.status_code}"
                    document.save(update_fields=['status', 'error_message'])

        except Exception as e:
            logger.error(f"Error triggering preprocessing for document {document.id}: {e}", exc_info=True)
            document.status = Document.STATUS_FAILED
            document.error_message = str(e)
            document.save(update_fields=['status', 'error_message'])

    def _trigger_indexing(self, document: Document, chunks: list):
        """
        Trigger document indexing via AI Service

        This sends the chunks to FastAPI for embedding generation and ChromaDB storage.
        The embedding IDs are then saved to DocumentChunk records.
        """
        if not chunks:
            return

        try:
            # Prepare chunks data
            chunks_data = []
            for chunk in chunks:
                chunks_data.append({
                    'chunk_index': chunk.chunk_index,
                    'text': chunk.text,
                    'start_offset': chunk.start_offset,
                    'end_offset': chunk.end_offset,
                    'token_count': chunk.token_count
                })

            # Prepare document metadata
            document_metadata = {
                'title': document.title,
                'doc_type': document.doc_type,
                'language': document.language,
                'file_type': document.file_type
            }

            # Call FastAPI indexing endpoint
            ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')
            response = httpx.post(
                f'{ai_service_url}/rag/index',
                json={
                    'document_id': str(document.id),
                    'chunks': chunks_data,
                    'document_metadata': document_metadata
                },
                timeout=120.0  # Longer timeout for embedding generation
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # Update embedding IDs in chunks
                    embedding_ids = result.get('embedding_ids', [])

                    for i, chunk in enumerate(chunks):
                        if i < len(embedding_ids):
                            chunk.embedding_id = embedding_ids[i]
                            chunk.save(update_fields=['embedding_id'])

                    # Update document status to EMBEDDED
                    document.status = Document.STATUS_EMBEDDED
                    document.save(update_fields=['status'])

                    logger.info(
                        f"Document {document.id} indexed successfully: "
                        f"{result.get('indexed_count', 0)} chunks embedded"
                    )
                else:
                    logger.error(f"Indexing failed for document {document.id}: {result.get('error')}")
                    document.status = Document.STATUS_FAILED
                    document.error_message = f"Indexing failed: {result.get('error')}"
                    document.save(update_fields=['status', 'error_message'])
            else:
                logger.error(
                    f"AI Service returned error for indexing document {document.id}: "
                    f"{response.status_code} - {response.text}"
                )
                document.status = Document.STATUS_FAILED
                document.error_message = f"Indexing error: {response.status_code}"
                document.save(update_fields=['status', 'error_message'])

        except Exception as e:
            logger.error(f"Error triggering indexing for document {document.id}: {e}", exc_info=True)
            document.status = Document.STATUS_FAILED
            document.error_message = str(e)
            document.save(update_fields=['status', 'error_message'])

    def _generate_summary(self, document: Document, llm_model: str) -> Summary:
        """
        Generate summary for a document via AI Service

        Calls FastAPI /v1/llm/summarize endpoint and saves the result to the database.
        """
        try:
            # Prepare document text from chunks
            chunks = document.chunks.all().order_by('chunk_index')
            document_text = '\n\n'.join([chunk.text for chunk in chunks])

            if not document_text:
                raise ValueError("No text content found in document chunks")

            # Call AI Service summarize endpoint
            ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')
            response = httpx.post(
                f'{ai_service_url}/v1/llm/summarize',
                json={
                    'document_id': str(document.id),
                    'text': document_text,
                    'llm_model': llm_model,
                    'summary_type': 'GLOBAL'
                },
                timeout=60.0
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # Save summary to database
                    summary = Summary.objects.create(
                        document=document,
                        llm_model=llm_model,
                        summary_type=Summary.SUMMARY_TYPE_GLOBAL,
                        content=result.get('summary', ''),
                        meta={
                            'token_count': result.get('token_count', 0),
                            'model_version': result.get('model_version', '')
                        }
                    )

                    logger.info(f"Summary generated for document {document.id} using {llm_model}")
                    return summary
                else:
                    raise Exception(f"AI Service error: {result.get('error', 'Unknown error')}")
            else:
                raise Exception(f"AI Service returned {response.status_code}: {response.text}")

        except httpx.RequestError as e:
            logger.error(f"Request error calling AI Service for summary: {e}", exc_info=True)
            raise Exception(f"Failed to connect to AI Service: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            raise

    def _extract_clauses(self, document: Document, llm_model: str) -> list:
        """
        Extract key clauses from a document via AI Service

        Calls FastAPI /v1/llm/clauses endpoint and saves the results to the database.
        """
        try:
            # Prepare document text from chunks
            chunks = document.chunks.all().order_by('chunk_index')
            document_text = '\n\n'.join([chunk.text for chunk in chunks])

            if not document_text:
                raise ValueError("No text content found in document chunks")

            # Call AI Service clause extraction endpoint
            ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')
            response = httpx.post(
                f'{ai_service_url}/v1/llm/clauses',
                json={
                    'document_id': str(document.id),
                    'text': document_text,
                    'llm_model': llm_model,
                    'doc_type': document.doc_type
                },
                timeout=60.0
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # Save clauses to database
                    clauses_data = result.get('clauses', [])
                    clause_objs = []

                    for clause_data in clauses_data:
                        clause = KeyClause.objects.create(
                            document=document,
                            clause_type=clause_data.get('clause_type', 'OTHER'),
                            title=clause_data.get('title', ''),
                            content=clause_data.get('content', ''),
                            importance_score=clause_data.get('importance_score', 50),
                            llm_model=llm_model
                        )
                        clause_objs.append(clause)

                    logger.info(
                        f"Extracted {len(clause_objs)} clauses for document {document.id} "
                        f"using {llm_model}"
                    )
                    return clause_objs
                else:
                    raise Exception(f"AI Service error: {result.get('error', 'Unknown error')}")
            else:
                raise Exception(f"AI Service returned {response.status_code}: {response.text}")

        except httpx.RequestError as e:
            logger.error(f"Request error calling AI Service for clauses: {e}", exc_info=True)
            raise Exception(f"Failed to connect to AI Service: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting clauses: {e}", exc_info=True)
            raise

    def _analyze_risk(self, document: Document, llm_model: str) -> RiskAnalysisResult:
        """
        Analyze risks in a document via AI Service

        Calls FastAPI /v1/llm/analyze_risk endpoint and saves the result to the database.
        """
        try:
            # Prepare document text from chunks
            chunks = document.chunks.all().order_by('chunk_index')
            document_text = '\n\n'.join([chunk.text for chunk in chunks])

            if not document_text:
                raise ValueError("No text content found in document chunks")

            # Call AI Service risk analysis endpoint
            ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')
            response = httpx.post(
                f'{ai_service_url}/v1/llm/analyze_risk',
                json={
                    'document_id': str(document.id),
                    'text': document_text,
                    'llm_model': llm_model,
                    'document_type': document.doc_type
                },
                timeout=90.0  # Longer timeout for risk analysis
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # Save risk analysis to database
                    risk_analysis = RiskAnalysisResult.objects.create(
                        document=document,
                        overall_risk_score=result.get('overall_risk_score', 0),
                        severity=result.get('severity', 'MEDIUM'),
                        risk_items=result.get('risk_items', []),
                        recommendations=result.get('recommendations', []),
                        summary=result.get('summary', ''),
                        llm_model=llm_model,
                        meta=result.get('meta', {})
                    )

                    logger.info(
                        f"Risk analysis completed for document {document.id}: "
                        f"Score={risk_analysis.overall_risk_score}, "
                        f"Severity={risk_analysis.severity}, "
                        f"Items={len(risk_analysis.risk_items)} "
                        f"using {llm_model}"
                    )
                    return risk_analysis
                else:
                    raise Exception(f"AI Service error: {result.get('error', 'Unknown error')}")
            else:
                raise Exception(f"AI Service returned {response.status_code}: {response.text}")

        except httpx.RequestError as e:
            logger.error(f"Request error calling AI Service for risk analysis: {e}", exc_info=True)
            raise Exception(f"Failed to connect to AI Service: {str(e)}")
        except Exception as e:
            logger.error(f"Error analyzing risks: {e}", exc_info=True)
            raise

    def _analyze_case(self, document: Document, llm_model: str, scenario: str) -> CaseAnalysis:
        """
        Analyze case details in a document via AI Service

        Calls FastAPI /v1/llm/analyze_case endpoint and saves the result to the database.
        """
        try:
            # Check if case analysis already exists
            if hasattr(document, 'case_analysis'):
                # Delete existing analysis to create a new one
                document.case_analysis.delete()

            # Prepare document text from chunks
            chunks = document.chunks.all().order_by('chunk_index')
            document_text = '\n\n'.join([chunk.text for chunk in chunks])

            if not document_text:
                raise ValueError("No text content found in document chunks")

            # Call AI Service case analysis endpoint
            ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')
            response = httpx.post(
                f'{ai_service_url}/v1/llm/analyze_case',
                json={
                    'document_id': str(document.id),
                    'text': document_text,
                    'llm_model': llm_model,
                    'scenario': scenario
                },
                timeout=90.0  # Longer timeout for case analysis
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # Save case analysis to database
                    case_analysis = CaseAnalysis.objects.create(
                        document=document,
                        suggested_case_name=result.get('suggested_case_name', document.title),
                        document_types=result.get('document_types', []),
                        parties=result.get('parties', {}),
                        key_dates=result.get('key_dates', {}),
                        issues=result.get('issues', []),
                        related_precedents=result.get('related_cases', []),
                        suggested_next_steps=result.get('suggested_next_steps', []),
                        scenario=scenario,
                        llm_model=llm_model
                    )

                    logger.info(
                        f"Case analysis completed for document {document.id}: "
                        f"Parties={len(case_analysis.parties)}, "
                        f"Issues={len(case_analysis.issues)}, "
                        f"Scenario={scenario} "
                        f"using {llm_model}"
                    )
                    return case_analysis
                else:
                    raise Exception(f"AI Service error: {result.get('error', 'Unknown error')}")
            else:
                raise Exception(f"AI Service returned {response.status_code}: {response.text}")

        except httpx.RequestError as e:
            logger.error(f"Request error calling AI Service for case analysis: {e}", exc_info=True)
            raise Exception(f"Failed to connect to AI Service: {str(e)}")
        except Exception as e:
            logger.error(f"Error analyzing case: {e}", exc_info=True)
            raise
