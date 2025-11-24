from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.conf import settings
import httpx
import logging

from .models import Document, DocumentChunk
from .serializers import (
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentDetailSerializer,
    DocumentChunkSerializer,
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
    parser_classes = [MultiPartParser, FormParser]

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

    @action(detail=False, methods=['post'], url_path='upload')
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
                        for chunk_data in chunks:
                            DocumentChunk.objects.create(
                                document=document,
                                chunk_index=chunk_data['chunk_index'],
                                text=chunk_data['text'],
                                start_offset=chunk_data.get('start_offset'),
                                end_offset=chunk_data.get('end_offset'),
                                token_count=chunk_data.get('token_count')
                            )

                        logger.info(
                            f"Document {document.id} preprocessed successfully: "
                            f"{len(chunks)} chunks created"
                        )
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
