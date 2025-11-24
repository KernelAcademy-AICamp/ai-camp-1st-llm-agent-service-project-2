from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q

from .models import Document, DocumentChunk
from .serializers import (
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentDetailSerializer,
    DocumentChunkSerializer,
)


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
