from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q, Avg, Count
from django.conf import settings
import httpx
import logging
import threading

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

        Query parameters:
        - doc_type: Filter by document type (CASE, CONTRACT, etc.)
        - status: Filter by status (UPLOADED, PREPROCESSED, etc.)
        - search: Search by title
        - date_from: Filter by created_at >= date (YYYY-MM-DD format)
        - date_to: Filter by created_at <= date (YYYY-MM-DD format)
        - risk_severity: Filter by risk severity (CRITICAL, HIGH, MEDIUM, LOW, INFO)
        - min_risk_score: Filter by minimum risk score (0-100)
        - max_risk_score: Filter by maximum risk score (0-100)
        - has_risk_analysis: Filter documents with/without risk analysis (true/false)
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

        # Filter by date range (created_at)
        date_from = request.query_params.get('date_from', None)
        if date_from:
            try:
                from datetime import datetime
                parsed_date = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=parsed_date.date())
            except ValueError:
                pass  # Invalid date format, ignore filter

        date_to = request.query_params.get('date_to', None)
        if date_to:
            try:
                from datetime import datetime
                parsed_date = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=parsed_date.date())
            except ValueError:
                pass  # Invalid date format, ignore filter

        # Search by title
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
            )

        # Filter by risk severity
        risk_severity = request.query_params.get('risk_severity', None)
        if risk_severity:
            queryset = queryset.filter(
                risk_analyses__severity=risk_severity
            ).distinct()

        # Filter by minimum risk score
        min_risk_score = request.query_params.get('min_risk_score', None)
        if min_risk_score:
            try:
                min_score = int(min_risk_score)
                queryset = queryset.filter(
                    risk_analyses__overall_risk_score__gte=min_score
                ).distinct()
            except ValueError:
                pass

        # Filter by maximum risk score
        max_risk_score = request.query_params.get('max_risk_score', None)
        if max_risk_score:
            try:
                max_score = int(max_risk_score)
                queryset = queryset.filter(
                    risk_analyses__overall_risk_score__lte=max_score
                ).distinct()
            except ValueError:
                pass

        # Filter documents with/without risk analysis
        has_risk_analysis = request.query_params.get('has_risk_analysis', None)
        if has_risk_analysis is not None:
            if has_risk_analysis.lower() == 'true':
                queryset = queryset.filter(risk_analyses__isnull=False).distinct()
            elif has_risk_analysis.lower() == 'false':
                queryset = queryset.filter(risk_analyses__isnull=True)

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

    @action(detail=False, methods=['post'], url_path='upload-and-analyze', parser_classes=[MultiPartParser, FormParser])
    def upload_and_analyze(self, request):
        """
        POST /api/v1/documents/upload-and-analyze/
        Upload a document and automatically start sequential analysis

        Analysis order (sequential, not parallel):
        1. Summary generation
        2. Clause extraction
        3. Risk analysis

        Each step updates analysis_status, allowing frontend to poll for progress.
        When one step completes, it's immediately available while others continue.

        Request body (multipart/form-data):
        - title: Document title (required)
        - doc_type: Document type (required) - CASE/CONTRACT/STATUTE/PRECEDENT/OTHER
        - language: Language (optional, default: ko)
        - original_file: File to upload (required)
        - confirmed_text: Pre-extracted text from OCR (optional). If provided, skips preprocessing.

        Response:
        - 201: Document uploaded, analysis started
        - 400: Validation error
        """
        serializer = DocumentUploadSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            document = serializer.save()

            # Get confirmed_text if provided (from OCR workflow)
            confirmed_text = request.data.get('confirmed_text', None)

            # Start preprocessing and analysis in background thread
            # This allows immediate response to client
            def run_analysis_pipeline(doc_id, pre_confirmed_text=None):
                try:
                    # Need to re-fetch document in thread context
                    from django.db import connection
                    connection.close()

                    doc = Document.objects.get(pk=doc_id)

                    # Update status to pending
                    doc.analysis_status = Document.ANALYSIS_PENDING
                    doc.save(update_fields=['analysis_status'])

                    # Step 1: Preprocessing or use confirmed text
                    if pre_confirmed_text:
                        # Use confirmed text directly (from OCR workflow)
                        logger.info(f"Using confirmed text for document {doc.id} (skipping preprocessing)")
                        self._create_chunks_from_text(doc, pre_confirmed_text)
                    else:
                        # Standard preprocessing from file
                        self._trigger_preprocessing(doc)

                    # Re-fetch after preprocessing
                    doc.refresh_from_db()

                    # Check if preprocessing succeeded
                    if doc.status not in [Document.STATUS_PREPROCESSED, Document.STATUS_EMBEDDED]:
                        doc.analysis_status = Document.ANALYSIS_FAILED
                        doc.analysis_error = 'Document preprocessing failed'
                        doc.save(update_fields=['analysis_status', 'analysis_error'])
                        return

                    # Step 2: Summary (sequential)
                    try:
                        doc.analysis_status = Document.ANALYSIS_SUMMARIZING
                        doc.save(update_fields=['analysis_status'])
                        self._generate_summary(doc, 'gpt-4')
                        logger.info(f"Summary completed for document {doc.id}")
                    except Exception as e:
                        logger.error(f"Summary failed for document {doc.id}: {e}")
                        # Continue with next step even if this fails

                    # Step 3: Clauses (sequential)
                    try:
                        doc.analysis_status = Document.ANALYSIS_EXTRACTING_CLAUSES
                        doc.save(update_fields=['analysis_status'])
                        self._extract_clauses(doc, 'gpt-4')
                        logger.info(f"Clause extraction completed for document {doc.id}")
                    except Exception as e:
                        logger.error(f"Clause extraction failed for document {doc.id}: {e}")
                        # Continue with next step even if this fails

                    # Step 4: Risk Analysis (sequential)
                    try:
                        doc.analysis_status = Document.ANALYSIS_ANALYZING_RISK
                        doc.save(update_fields=['analysis_status'])
                        self._analyze_risk(doc, 'gpt-4')
                        logger.info(f"Risk analysis completed for document {doc.id}")
                    except Exception as e:
                        logger.error(f"Risk analysis failed for document {doc.id}: {e}")

                    # Mark as completed
                    doc.analysis_status = Document.ANALYSIS_COMPLETED
                    doc.save(update_fields=['analysis_status'])
                    logger.info(f"All analysis completed for document {doc.id}")

                except Exception as e:
                    logger.error(f"Analysis pipeline failed for document {doc_id}: {e}", exc_info=True)
                    try:
                        doc = Document.objects.get(pk=doc_id)
                        doc.analysis_status = Document.ANALYSIS_FAILED
                        doc.analysis_error = str(e)
                        doc.save(update_fields=['analysis_status', 'analysis_error'])
                    except Exception:
                        pass

            # Start analysis in background thread
            thread = threading.Thread(target=run_analysis_pipeline, args=(str(document.id), confirmed_text))
            thread.daemon = True
            thread.start()

            # Return immediately with document info
            response_serializer = DocumentSerializer(document)
            return Response(
                {
                    'message': 'Document uploaded, analysis started',
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

    @action(detail=True, methods=['get'], url_path='analysis-status')
    def analysis_status(self, request, pk=None):
        """
        GET /api/v1/documents/{id}/analysis-status/
        Get current analysis status for polling

        Response:
        {
            "document_id": "...",
            "analysis_status": "summarizing" | "extracting_clauses" | "analyzing_risk" | "completed" | "failed",
            "analysis_status_display": "Summarizing",
            "has_summary": true,
            "has_clauses": true,
            "clause_count": 5,
            "has_risk_analysis": false
        }
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check what analysis results exist
        has_summary = document.summaries.filter(summary_type=Summary.SUMMARY_TYPE_GLOBAL).exists()
        has_clauses = document.key_clauses.exists()
        clause_count = document.key_clauses.count()
        has_risk_analysis = document.risk_analyses.exists()

        return Response({
            'document_id': str(document.id),
            'document_title': document.title,
            'analysis_status': document.analysis_status,
            'analysis_status_display': document.get_analysis_status_display(),
            'analysis_error': document.analysis_error,
            'has_summary': has_summary,
            'has_clauses': has_clauses,
            'clause_count': clause_count,
            'has_risk_analysis': has_risk_analysis
        })

    @action(detail=True, methods=['post'], url_path='start-analysis')
    def start_analysis(self, request, pk=None):
        """
        POST /api/v1/documents/{id}/start-analysis/
        Start sequential analysis for an existing document

        Use this to re-run analysis or start analysis for a previously uploaded document.
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

        # Check if analysis is already running
        if document.analysis_status in [
            Document.ANALYSIS_PENDING,
            Document.ANALYSIS_SUMMARIZING,
            Document.ANALYSIS_EXTRACTING_CLAUSES,
            Document.ANALYSIS_ANALYZING_RISK
        ]:
            return Response(
                {
                    'error': 'Analysis already in progress',
                    'analysis_status': document.analysis_status
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Start analysis in background thread
        def run_analysis_pipeline(doc_id):
            try:
                from django.db import connection
                connection.close()

                doc = Document.objects.get(pk=doc_id)

                # Step 1: Summary
                try:
                    doc.analysis_status = Document.ANALYSIS_SUMMARIZING
                    doc.save(update_fields=['analysis_status'])
                    self._generate_summary(doc, 'gpt-4')
                except Exception as e:
                    logger.error(f"Summary failed for document {doc.id}: {e}")

                # Step 2: Clauses
                try:
                    doc.analysis_status = Document.ANALYSIS_EXTRACTING_CLAUSES
                    doc.save(update_fields=['analysis_status'])
                    self._extract_clauses(doc, 'gpt-4')
                except Exception as e:
                    logger.error(f"Clause extraction failed for document {doc.id}: {e}")

                # Step 3: Risk Analysis
                try:
                    doc.analysis_status = Document.ANALYSIS_ANALYZING_RISK
                    doc.save(update_fields=['analysis_status'])
                    self._analyze_risk(doc, 'gpt-4')
                except Exception as e:
                    logger.error(f"Risk analysis failed for document {doc.id}: {e}")

                # Mark as completed
                doc.analysis_status = Document.ANALYSIS_COMPLETED
                doc.save(update_fields=['analysis_status'])

            except Exception as e:
                logger.error(f"Analysis pipeline failed: {e}", exc_info=True)
                try:
                    doc = Document.objects.get(pk=doc_id)
                    doc.analysis_status = Document.ANALYSIS_FAILED
                    doc.analysis_error = str(e)
                    doc.save(update_fields=['analysis_status', 'analysis_error'])
                except Exception:
                    pass

        thread = threading.Thread(target=run_analysis_pipeline, args=(str(document.id),))
        thread.daemon = True
        thread.start()

        # Update status immediately
        document.analysis_status = Document.ANALYSIS_PENDING
        document.analysis_error = None
        document.save(update_fields=['analysis_status', 'analysis_error'])

        return Response({
            'message': 'Analysis started',
            'document_id': str(document.id),
            'analysis_status': document.analysis_status
        })

    @action(detail=False, methods=['get'], url_path='risk-overview')
    def risk_overview(self, request):
        """
        GET /api/v1/documents/risk-overview/
        Get risk analysis statistics overview for the current user's documents

        Response:
        {
            "total_documents": 50,
            "documents_with_risk": 30,
            "documents_without_risk": 20,
            "avg_risk_score": 45.5,
            "high_risk_count": 5,  // documents with score >= 70
            "severity_distribution": {
                "CRITICAL": 2,
                "HIGH": 8,
                "MEDIUM": 15,
                "LOW": 5,
                "INFO": 0
            },
            "category_distribution": {
                "LEGAL": 10,
                "FINANCIAL": 8,
                "COMPLIANCE": 12,
                "OPERATIONAL": 5,
                "REPUTATIONAL": 3,
                "OTHER": 2
            },
            "recent_analyses": [...]  // Top 5 most recent risk analyses
        }
        """
        queryset = self.get_queryset()
        total_documents = queryset.count()

        # Get documents with risk analysis
        documents_with_risk = queryset.filter(
            risk_analyses__isnull=False
        ).distinct()
        documents_with_risk_count = documents_with_risk.count()
        documents_without_risk_count = total_documents - documents_with_risk_count

        # Get average risk score (from most recent analysis per document)
        from django.db.models import Subquery, OuterRef

        # Get the most recent risk analysis for each document
        latest_risk_ids = RiskAnalysisResult.objects.filter(
            document__user=request.user
        ).order_by('document_id', '-created_at').distinct('document_id').values_list('id', flat=True)

        latest_risks = RiskAnalysisResult.objects.filter(id__in=latest_risk_ids)

        avg_risk_score = latest_risks.aggregate(
            avg=Avg('overall_risk_score')
        )['avg'] or 0

        # Count high risk documents (score >= 70)
        high_risk_count = latest_risks.filter(overall_risk_score__gte=70).count()

        # Severity distribution
        severity_distribution = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0,
            'INFO': 0
        }
        severity_counts = latest_risks.values('severity').annotate(count=Count('id'))
        for item in severity_counts:
            if item['severity'] in severity_distribution:
                severity_distribution[item['severity']] = item['count']

        # Category distribution (from risk_items JSON field)
        category_distribution = {
            'LEGAL': 0,
            'FINANCIAL': 0,
            'COMPLIANCE': 0,
            'OPERATIONAL': 0,
            'REPUTATIONAL': 0,
            'OTHER': 0
        }

        # Count categories from risk items
        for risk in latest_risks:
            if risk.risk_items:
                for item in risk.risk_items:
                    category = item.get('category', 'OTHER')
                    if category in category_distribution:
                        category_distribution[category] += 1
                    else:
                        category_distribution['OTHER'] += 1

        # Get recent risk analyses (top 5)
        recent_analyses = RiskAnalysisResult.objects.filter(
            document__user=request.user
        ).select_related('document').order_by('-created_at')[:5]

        recent_analyses_data = []
        for analysis in recent_analyses:
            recent_analyses_data.append({
                'id': str(analysis.id),
                'document_id': str(analysis.document.id),
                'document_title': analysis.document.title,
                'overall_risk_score': analysis.overall_risk_score,
                'severity': analysis.severity,
                'risk_item_count': len(analysis.risk_items) if analysis.risk_items else 0,
                'created_at': analysis.created_at.isoformat()
            })

        return Response({
            'total_documents': total_documents,
            'documents_with_risk': documents_with_risk_count,
            'documents_without_risk': documents_without_risk_count,
            'avg_risk_score': round(avg_risk_score, 1),
            'high_risk_count': high_risk_count,
            'severity_distribution': severity_distribution,
            'category_distribution': category_distribution,
            'recent_analyses': recent_analyses_data
        })

    @action(detail=False, methods=['get'], url_path='with-risk')
    def documents_with_risk(self, request):
        """
        GET /api/v1/documents/with-risk/
        Get documents with risk analysis, including risk details

        Query parameters:
        - severity: Filter by severity (CRITICAL, HIGH, MEDIUM, LOW, INFO)
        - min_score: Minimum risk score (0-100)
        - max_score: Maximum risk score (0-100)
        - sort_by: Sort by field (risk_score, created_at, title)
        - order: Sort order (asc, desc)
        - page: Page number (default: 1)
        - page_size: Items per page (default: 10)

        Response includes document info with latest risk analysis
        """
        queryset = self.get_queryset().filter(
            risk_analyses__isnull=False
        ).distinct()

        # Apply filters
        severity = request.query_params.get('severity', None)
        if severity:
            queryset = queryset.filter(risk_analyses__severity=severity)

        min_score = request.query_params.get('min_score', None)
        if min_score:
            try:
                queryset = queryset.filter(
                    risk_analyses__overall_risk_score__gte=int(min_score)
                )
            except ValueError:
                pass

        max_score = request.query_params.get('max_score', None)
        if max_score:
            try:
                queryset = queryset.filter(
                    risk_analyses__overall_risk_score__lte=int(max_score)
                )
            except ValueError:
                pass

        # Get sorting parameters
        sort_by = request.query_params.get('sort_by', 'created_at')
        order = request.query_params.get('order', 'desc')

        # Build results with risk analysis data
        results = []
        for doc in queryset:
            # Get the most recent risk analysis for this document
            latest_risk = doc.risk_analyses.order_by('-created_at').first()
            if latest_risk:
                results.append({
                    'document': DocumentSerializer(doc).data,
                    'risk_analysis': {
                        'id': str(latest_risk.id),
                        'overall_risk_score': latest_risk.overall_risk_score,
                        'severity': latest_risk.severity,
                        'risk_item_count': len(latest_risk.risk_items) if latest_risk.risk_items else 0,
                        'summary': latest_risk.summary,
                        'llm_model': latest_risk.llm_model,
                        'created_at': latest_risk.created_at.isoformat()
                    }
                })

        # Sort results
        if sort_by == 'risk_score':
            results.sort(
                key=lambda x: x['risk_analysis']['overall_risk_score'],
                reverse=(order == 'desc')
            )
        elif sort_by == 'title':
            results.sort(
                key=lambda x: x['document']['title'].lower(),
                reverse=(order == 'desc')
            )
        else:  # default: created_at
            results.sort(
                key=lambda x: x['risk_analysis']['created_at'],
                reverse=(order == 'desc')
            )

        # Pagination
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
        except ValueError:
            page = 1
            page_size = 10

        total_count = len(results)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = results[start_idx:end_idx]

        return Response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'results': paginated_results
        })

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

    @action(detail=True, methods=['post'], url_path='extract_clauses_preview')
    def extract_clauses_preview(self, request, pk=None):
        """
        POST /api/v1/documents/{id}/extract_clauses_preview/
        Extract clauses preview WITHOUT saving to DB

        This allows users to see extracted clauses before deciding which ones to add.

        Response:
        {
            "success": true,
            "document_id": "...",
            "clauses": [
                {
                    "clause_type": "...",
                    "title": "...",
                    "content": "...",
                    "importance_score": 80
                }
            ]
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

        try:
            # Extract clauses WITHOUT saving
            clauses_data = self._extract_clauses_preview(document)

            return Response({
                'success': True,
                'document_id': str(document.id),
                'document_title': document.title,
                'clauses': clauses_data,
                'clause_count': len(clauses_data)
            })

        except Exception as e:
            logger.error(f"Error extracting clauses preview for document {document.id}: {e}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='save_selected_clauses')
    def save_selected_clauses(self, request, pk=None):
        """
        POST /api/v1/documents/{id}/save_selected_clauses/
        Save only selected clauses to the database

        Request body:
        {
            "clauses": [
                {
                    "clause_type": "...",
                    "title": "...",
                    "content": "...",
                    "importance_score": 80
                }
            ]
        }

        Response:
        {
            "success": true,
            "document_id": "...",
            "saved_count": 3,
            "clauses": [...]
        }
        """
        try:
            document = self.get_queryset().get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        clauses_data = request.data.get('clauses', [])

        if not clauses_data:
            return Response(
                {'error': 'No clauses provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            saved_clauses = []
            llm_model = request.data.get('llm_model', 'gpt-4')

            for clause_data in clauses_data:
                clause = KeyClause.objects.create(
                    document=document,
                    clause_type=clause_data.get('clause_type', 'OTHER'),
                    title=clause_data.get('title', ''),
                    content=clause_data.get('content', ''),
                    importance_score=clause_data.get('importance_score', 50),
                    llm_model=llm_model
                )
                saved_clauses.append(clause)

            logger.info(
                f"Saved {len(saved_clauses)} selected clauses for document {document.id}"
            )

            return Response({
                'success': True,
                'document_id': str(document.id),
                'saved_count': len(saved_clauses),
                'clauses': KeyClauseSerializer(saved_clauses, many=True).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error saving selected clauses for document {document.id}: {e}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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

    def _create_chunks_from_text(self, document: Document, confirmed_text: str):
        """
        Create chunks from confirmed text (OCR workflow).

        This bypasses the preprocessing step when text is already extracted and confirmed
        via the OCR review workflow.

        Args:
            document: Document object
            confirmed_text: Pre-extracted and confirmed text from OCR
        """
        try:
            if not confirmed_text or not confirmed_text.strip():
                raise ValueError("Confirmed text is empty")

            # Chunk parameters (same as preprocessing)
            chunk_size = 1000
            chunk_overlap = 200

            # Simple text chunking
            text = confirmed_text.strip()
            chunks_data = []

            if len(text) <= chunk_size:
                # Single chunk
                chunks_data.append({
                    'chunk_index': 0,
                    'text': text,
                    'start_offset': 0,
                    'end_offset': len(text),
                    'token_count': len(text.split())
                })
            else:
                # Multiple chunks with overlap
                start = 0
                chunk_index = 0
                while start < len(text):
                    end = start + chunk_size
                    chunk_text = text[start:end]

                    # Try to break at sentence/paragraph boundary if not at end
                    if end < len(text):
                        # Find last period, newline, or space
                        last_break = max(
                            chunk_text.rfind('. '),
                            chunk_text.rfind('.\n'),
                            chunk_text.rfind('\n\n'),
                            chunk_text.rfind('\n')
                        )
                        if last_break > chunk_size * 0.5:  # Only if found in latter half
                            chunk_text = chunk_text[:last_break + 1]
                            end = start + len(chunk_text)

                    chunks_data.append({
                        'chunk_index': chunk_index,
                        'text': chunk_text.strip(),
                        'start_offset': start,
                        'end_offset': end,
                        'token_count': len(chunk_text.split())
                    })

                    # Move start with overlap
                    start = end - chunk_overlap
                    if start >= len(text) - chunk_overlap:
                        break
                    chunk_index += 1

            # Save chunks to database
            chunk_objects = []
            for chunk_data in chunks_data:
                chunk_obj = DocumentChunk.objects.create(
                    document=document,
                    chunk_index=chunk_data['chunk_index'],
                    text=chunk_data['text'],
                    start_offset=chunk_data.get('start_offset'),
                    end_offset=chunk_data.get('end_offset'),
                    token_count=chunk_data.get('token_count')
                )
                chunk_objects.append(chunk_obj)

            # Update document status
            document.status = Document.STATUS_PREPROCESSED
            document.save(update_fields=['status'])

            logger.info(
                f"Document {document.id} chunks created from confirmed text: "
                f"{len(chunk_objects)} chunks"
            )

            # Optionally trigger indexing
            try:
                self._trigger_indexing(document, chunk_objects)
            except Exception as e:
                logger.warning(f"Failed to trigger indexing for document {document.id}: {e}")
                # Don't fail if indexing fails

        except Exception as e:
            logger.error(f"Error creating chunks from confirmed text for document {document.id}: {e}", exc_info=True)
            document.status = Document.STATUS_FAILED
            document.error_message = str(e)
            document.save(update_fields=['status', 'error_message'])

    def _trigger_indexing(self, document: Document, chunks: list):
        """
        Trigger document indexing via AI Service

        This sends the chunks to FastAPI for embedding generation and Qdrant storage.
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
                    # Indexing failed but don't change status - document can still be analyzed
                    logger.warning(
                        f"Indexing failed for document {document.id}: {result.get('error')}. "
                        f"Document remains in PREPROCESSED state for analysis."
                    )
            else:
                # Indexing API error but don't change status - document can still be analyzed
                logger.warning(
                    f"AI Service returned error for indexing document {document.id}: "
                    f"{response.status_code} - {response.text}. "
                    f"Document remains in PREPROCESSED state for analysis."
                )

        except Exception as e:
            # Indexing exception but don't change status - document can still be analyzed
            logger.warning(
                f"Error triggering indexing for document {document.id}: {e}. "
                f"Document remains in PREPROCESSED state for analysis."
            )

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

            # Call AI Service v2 documents/analyze endpoint (요약만 요청)
            ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')
            import uuid
            response = httpx.post(
                f'{ai_service_url}/v2/documents/analyze/text',
                json={
                    'document_id': str(document.id),
                    'text': document_text,
                    'doc_type': document.doc_type or 'OTHER',
                    'session_id': str(uuid.uuid4()),
                    'analysis_type': 'summary'  # 요약만 요청
                },
                timeout=60.0
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # v2 응답에서 summary 추출 (v2는 SummaryV2 객체 반환)
                    summary_data = result.get('summary')
                    if isinstance(summary_data, dict):
                        # v2 API: {"summary": {"summary": "...", "token_count": N, ...}}
                        summary_content = summary_data.get('summary', '')
                        token_count = summary_data.get('token_count', 0)
                        model_version = summary_data.get('model_version', '')
                    elif isinstance(summary_data, str):
                        # 문자열로 바로 반환된 경우
                        summary_content = summary_data
                        token_count = 0
                        model_version = ''
                    else:
                        summary_content = ''
                        token_count = 0
                        model_version = ''

                    # Save summary to database
                    summary = Summary.objects.create(
                        document=document,
                        llm_model=llm_model,
                        summary_type=Summary.SUMMARY_TYPE_GLOBAL,
                        content=summary_content,
                        meta={
                            'token_count': token_count,
                            'model_version': model_version,
                            'session_id': result.get('session_id', ''),
                            'version': 'v2'
                        }
                    )

                    logger.info(f"Summary generated for document {document.id} using {llm_model} (v2 API)")
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

            # Call AI Service v2 documents/analyze endpoint (조항만 요청)
            ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')
            import uuid
            response = httpx.post(
                f'{ai_service_url}/v2/documents/analyze/text',
                json={
                    'document_id': str(document.id),
                    'text': document_text,
                    'doc_type': document.doc_type or 'OTHER',
                    'session_id': str(uuid.uuid4()),
                    'analysis_type': 'clauses'  # 조항만 요청
                },
                timeout=60.0
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # v2 응답에서 clauses 추출 (ClauseV2 객체 리스트 -> dict 리스트로 직렬화됨)
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
                        f"using {llm_model} (v2 API)"
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

            # Call AI Service v2 risk/analyze endpoint
            ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')
            import uuid
            session_id = str(uuid.uuid4())
            response = httpx.post(
                f'{ai_service_url}/v2/risk/analyze',
                json={
                    'text': document_text,
                    'doc_type': document.doc_type or 'CONTRACT',
                    'document_id': str(document.id),
                    'session_id': session_id
                },
                timeout=90.0  # Longer timeout for risk analysis
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # v2 응답에서 리스크 정보 추출
                    identified_risks = result.get('identified_risks', [])

                    # severity → score 변환 함수
                    def severity_to_score(severity: str) -> int:
                        scores = {
                            'CRITICAL': 100,
                            'HIGH': 75,
                            'MEDIUM': 50,
                            'LOW': 25,
                            'INFO': 10
                        }
                        return scores.get(severity, 50)

                    # 리스크 아이템을 프론트엔드 형식으로 변환
                    # 프론트엔드 RiskItem: category, title, description, severity, score, clause_reference
                    risk_items = []
                    for i, risk in enumerate(identified_risks, 1):
                        risk_type = risk.get('risk_type', 'OTHER')
                        severity = risk.get('severity', 'MEDIUM')
                        description = risk.get('description', '')
                        clause_ref = risk.get('clause_reference', '')

                        # title 생성: clause_reference가 있으면 사용, 없으면 risk_type + 번호
                        if clause_ref:
                            title = f"{clause_ref} 관련 리스크"
                        else:
                            title = f"{risk_type} 리스크 #{i}"

                        risk_items.append({
                            'category': risk_type,  # risk_type → category
                            'title': title,
                            'description': description,
                            'severity': severity,
                            'score': severity_to_score(severity),
                            'clause_reference': clause_ref,
                            # 레거시 필드 (호환성)
                            'risk_type': risk_type,
                            'recommendation': risk.get('recommendation', '')
                        })

                    # 심각도 결정 (가장 높은 심각도)
                    severity_order = ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
                    max_severity = 'MEDIUM'
                    for risk in identified_risks:
                        risk_sev = risk.get('severity', 'MEDIUM')
                        if severity_order.index(risk_sev) > severity_order.index(max_severity):
                            max_severity = risk_sev

                    # AI Service에서 계산된 overall_score 사용 (없으면 폴백 계산)
                    severity_assessment = result.get('severity_assessment', {})
                    overall_score = severity_assessment.get('overall_score')
                    if overall_score is None:
                        # 폴백: 리스크 아이템의 평균 점수
                        if risk_items:
                            overall_score = sum(item['score'] for item in risk_items) / len(risk_items)
                        else:
                            overall_score = 0

                    # Save risk analysis to database
                    # summary: 간결한 요약 (프론트엔드 표시용), report: 상세 보고서
                    # summary가 없으면 report를 폴백으로 사용
                    risk_summary = result.get('summary') or result.get('report', '')
                    risk_analysis = RiskAnalysisResult.objects.create(
                        document=document,
                        overall_risk_score=int(overall_score),
                        severity=max_severity,
                        risk_items=risk_items,
                        recommendations=[r.get('recommendation', '') for r in identified_risks if r.get('recommendation')],
                        summary=risk_summary,
                        llm_model=llm_model,
                        meta={
                            'session_id': result.get('session_id', session_id),
                            'requires_human_review': result.get('requires_human_review', False),
                            'awaiting_review': result.get('awaiting_review', False),
                            'version': 'v2',
                            'report': result.get('report', '')  # 상세 보고서 meta에 저장
                        }
                    )

                    logger.info(
                        f"Risk analysis completed for document {document.id}: "
                        f"Score={risk_analysis.overall_risk_score}, "
                        f"Severity={risk_analysis.severity}, "
                        f"Items={len(risk_analysis.risk_items)} "
                        f"using {llm_model} (v2 API)"
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

            # Call AI Service v2 cases/analyze endpoint
            ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')
            import uuid
            response = httpx.post(
                f'{ai_service_url}/v2/cases/analyze',
                json={
                    'case_content': document_text,
                    'case_type': scenario or 'other',
                    'session_id': str(uuid.uuid4())
                },
                timeout=90.0  # Longer timeout for case analysis
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # v2 응답에서 분석 결과 추출
                    # v2 API는 parties, issues, related_precedents를 최상위 레벨에서 반환
                    # analysis는 종합 분석 문자열 (dict가 아님)

                    # parties 파싱 (PartyV2 객체 리스트 → dict로 변환)
                    parties_data = result.get('parties', [])
                    parties_dict = {}
                    for party in parties_data:
                        if isinstance(party, dict):
                            role = party.get('role', 'unknown')
                            name = party.get('name', '')
                            desc = party.get('description', '')
                            if role not in parties_dict:
                                parties_dict[role] = []
                            parties_dict[role].append({'name': name, 'description': desc})

                    # issues 파싱 (IssueV2 객체 리스트)
                    issues_data = result.get('issues', [])
                    issues_list = []
                    for issue in issues_data:
                        if isinstance(issue, dict):
                            issues_list.append({
                                'type': issue.get('issue_type', ''),
                                'description': issue.get('description', ''),
                                'legal_basis': issue.get('legal_basis', '')
                            })

                    # related_precedents 파싱 (PrecedentV2 객체 리스트)
                    precedents_data = result.get('related_precedents', [])
                    precedents_list = []
                    for prec in precedents_data:
                        if isinstance(prec, dict):
                            precedents_list.append({
                                'case_number': prec.get('case_number', ''),
                                'title': prec.get('title', ''),
                                'summary': prec.get('summary', ''),
                                'relevance_score': prec.get('relevance_score', 0.0)
                            })

                    # analysis 문자열에서 추가 정보 추출 시도
                    analysis_text = result.get('analysis', '') or ''

                    # Save case analysis to database
                    case_analysis = CaseAnalysis.objects.create(
                        document=document,
                        suggested_case_name=document.title,  # v2에서는 별도 제공 안 함
                        document_types=[result.get('case_type', scenario)],  # case_type 사용
                        parties=parties_dict,
                        key_dates={},  # v2에서는 별도 제공 안 함
                        issues=issues_list,
                        related_precedents=precedents_list,
                        suggested_next_steps=[],  # v2에서는 별도 제공 안 함
                        scenario=scenario,
                        llm_model=llm_model
                    )

                    logger.info(
                        f"Case analysis completed for document {document.id}: "
                        f"Parties={len(case_analysis.parties)}, "
                        f"Issues={len(case_analysis.issues)}, "
                        f"Scenario={scenario} "
                        f"using {llm_model} (v2 API)"
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

    @action(detail=False, methods=['post'], url_path='create-from-text', parser_classes=[JSONParser])
    def create_from_text(self, request):
        """
        POST /api/v1/documents/create-from-text/
        Create a document from text content (no file upload)

        Used by Agent Hub to save analysis results.

        Request body:
        {
            "title": "Document Title",
            "doc_type": "CONTRACT",
            "text_content": "Full document text...",
            "source_type": "AGENT_HUB",
            "metadata": {...}
        }

        Response:
        {
            "message": "Document created successfully",
            "document": {...}
        }
        """
        # 서비스 인증 또는 사용자 인증 확인
        service_auth = request.headers.get('X-Service-Auth')
        user_id = request.headers.get('X-User-Id')

        if service_auth == 'agent-hub-internal' and user_id:
            # 내부 서비스 호출 - user_id로 사용자 조회
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': f'User not found: {user_id}'},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif request.user.is_authenticated:
            user = request.user
        else:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        title = request.data.get('title')
        doc_type = request.data.get('doc_type', 'OTHER')
        text_content = request.data.get('text_content')
        source_type = request.data.get('source_type', 'API')
        metadata = request.data.get('metadata', {})

        if not title or not text_content:
            return Response(
                {'error': 'title and text_content are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 문서 생성
            document = Document.objects.create(
                user=user,
                title=title,
                doc_type=doc_type,
                source_type=source_type,
                status=Document.STATUS_PREPROCESSED,  # 텍스트가 이미 있으므로 PREPROCESSED
                analysis_status=Document.ANALYSIS_COMPLETED if metadata.get('created_from') == 'agent_hub_save' else Document.ANALYSIS_NONE
            )

            # 텍스트를 청크로 저장 (단일 청크로 저장)
            # 필요시 청킹 로직 추가 가능
            chunk = DocumentChunk.objects.create(
                document=document,
                chunk_index=0,
                text=text_content,
                token_count=len(text_content.split())  # 대략적인 토큰 수
            )

            logger.info(
                f"Document created from text: {document.id}, "
                f"title='{title}', user={user.id}"
            )

            serializer = DocumentSerializer(document)
            return Response(
                {
                    'message': 'Document created successfully',
                    'document': serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Error creating document from text: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='save-summary', parser_classes=[JSONParser])
    def save_summary(self, request, pk=None):
        """
        POST /api/v1/documents/{id}/save-summary/
        Save a summary for a document (from Agent Hub)

        Request body:
        {
            "content": "Summary text...",
            "summary_type": "GLOBAL",
            "llm_model": "agent-hub",
            "source": "agent_hub"
        }
        """
        # 서비스 인증 또는 사용자 인증 확인
        service_auth = request.headers.get('X-Service-Auth')
        user_id = request.headers.get('X-User-Id')

        if service_auth == 'agent-hub-internal' and user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                document = Document.objects.get(pk=pk, user_id=user_id)
            except Document.DoesNotExist:
                return Response(
                    {'error': 'Document not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            try:
                document = self.get_queryset().get(pk=pk)
            except Document.DoesNotExist:
                return Response(
                    {'error': 'Document not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        content = request.data.get('content')
        summary_type = request.data.get('summary_type', 'GLOBAL')
        llm_model = request.data.get('llm_model', 'agent-hub')

        if not content:
            return Response(
                {'error': 'content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            summary = Summary.objects.create(
                document=document,
                content=content,
                summary_type=summary_type,
                llm_model=llm_model,
                meta={
                    'source': request.data.get('source', 'agent_hub')
                }
            )

            logger.info(f"Summary saved for document {document.id}")

            return Response(
                {
                    'success': True,
                    'summary_id': str(summary.id)
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Error saving summary: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='save-risk-analysis', parser_classes=[JSONParser])
    def save_risk_analysis(self, request, pk=None):
        """
        POST /api/v1/documents/{id}/save-risk-analysis/
        Save risk analysis for a document (from Agent Hub)

        Request body:
        {
            "overall_risk_score": 65,
            "severity": "MEDIUM",
            "risk_items": [...],
            "recommendations": [...],
            "summary": "Risk analysis summary...",
            "llm_model": "agent-hub"
        }
        """
        # 서비스 인증 또는 사용자 인증 확인
        service_auth = request.headers.get('X-Service-Auth')
        user_id = request.headers.get('X-User-Id')

        if service_auth == 'agent-hub-internal' and user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                document = Document.objects.get(pk=pk, user_id=user_id)
            except Document.DoesNotExist:
                return Response(
                    {'error': 'Document not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            try:
                document = self.get_queryset().get(pk=pk)
            except Document.DoesNotExist:
                return Response(
                    {'error': 'Document not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        try:
            risk_analysis = RiskAnalysisResult.objects.create(
                document=document,
                overall_risk_score=request.data.get('overall_risk_score', 50),
                severity=request.data.get('severity', 'MEDIUM'),
                risk_items=request.data.get('risk_items', []),
                recommendations=request.data.get('recommendations', []),
                summary=request.data.get('summary', ''),
                llm_model=request.data.get('llm_model', 'agent-hub'),
                meta={
                    'source': request.data.get('source', 'agent_hub')
                }
            )

            logger.info(f"Risk analysis saved for document {document.id}")

            return Response(
                {
                    'success': True,
                    'risk_analysis_id': str(risk_analysis.id)
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Error saving risk analysis: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _extract_clauses_preview(self, document: Document) -> list:
        """
        Extract key clauses from a document via AI Service WITHOUT saving to DB

        Returns a list of clause dictionaries for preview.
        """
        try:
            # Prepare document text from chunks
            chunks = document.chunks.all().order_by('chunk_index')
            document_text = '\n\n'.join([chunk.text for chunk in chunks])

            if not document_text:
                raise ValueError("No text content found in document chunks")

            # Call AI Service v2 documents/analyze endpoint (조항만 요청)
            ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')
            import uuid
            response = httpx.post(
                f'{ai_service_url}/v2/documents/analyze/text',
                json={
                    'document_id': str(document.id),
                    'text': document_text,
                    'doc_type': document.doc_type or 'OTHER',
                    'session_id': str(uuid.uuid4()),
                    'analysis_type': 'clauses'  # 조항만 요청
                },
                timeout=60.0
            )

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    # v2 응답에서 clauses 추출 (DB 저장 없이 반환)
                    clauses_data = result.get('clauses', [])
                    return clauses_data
                else:
                    raise Exception(f"AI Service error: {result.get('error', 'Unknown error')}")
            else:
                raise Exception(f"AI Service returned {response.status_code}: {response.text}")

        except httpx.RequestError as e:
            logger.error(f"Request error calling AI Service for clauses preview: {e}", exc_info=True)
            raise Exception(f"Failed to connect to AI Service: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting clauses preview: {e}", exc_info=True)
            raise
