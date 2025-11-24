import uuid
from django.db import models
from django.conf import settings


class Document(models.Model):
    """
    Document model for managing uploaded legal documents (contracts, statutes, etc.)

    Status flow: UPLOADED -> OCR_DONE -> PREPROCESSED -> EMBEDDED
    """

    # Document types
    DOC_TYPE_CASE = 'CASE'
    DOC_TYPE_CONTRACT = 'CONTRACT'
    DOC_TYPE_STATUTE = 'STATUTE'
    DOC_TYPE_PRECEDENT = 'PRECEDENT'
    DOC_TYPE_OTHER = 'OTHER'

    DOC_TYPE_CHOICES = [
        (DOC_TYPE_CASE, 'Case Document'),
        (DOC_TYPE_CONTRACT, 'Contract'),
        (DOC_TYPE_STATUTE, 'Statute'),
        (DOC_TYPE_PRECEDENT, 'Precedent'),
        (DOC_TYPE_OTHER, 'Other'),
    ]

    # Source types
    SOURCE_UPLOAD = 'UPLOAD'
    SOURCE_CRAWLED = 'CRAWLED'
    SOURCE_API = 'API'

    SOURCE_TYPE_CHOICES = [
        (SOURCE_UPLOAD, 'User Upload'),
        (SOURCE_CRAWLED, 'Web Crawled'),
        (SOURCE_API, 'External API'),
    ]

    # Processing status
    STATUS_UPLOADED = 'UPLOADED'
    STATUS_OCR_DONE = 'OCR_DONE'
    STATUS_PREPROCESSED = 'PREPROCESSED'
    STATUS_EMBEDDED = 'EMBEDDED'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_UPLOADED, 'Uploaded'),
        (STATUS_OCR_DONE, 'OCR Done'),
        (STATUS_PREPROCESSED, 'Preprocessed'),
        (STATUS_EMBEDDED, 'Embedded'),
        (STATUS_FAILED, 'Processing Failed'),
    ]

    # Language choices
    LANGUAGE_KO = 'ko'
    LANGUAGE_EN = 'en'

    LANGUAGE_CHOICES = [
        (LANGUAGE_KO, 'Korean'),
        (LANGUAGE_EN, 'English'),
    ]

    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents',
        help_text='Document owner'
    )
    title = models.CharField(
        max_length=500,
        help_text='Document title'
    )
    doc_type = models.CharField(
        max_length=20,
        choices=DOC_TYPE_CHOICES,
        default=DOC_TYPE_OTHER,
        help_text='Type of document'
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default=SOURCE_UPLOAD,
        help_text='How the document was obtained'
    )
    original_file = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text='Original uploaded file (PDF, DOCX, etc.)'
    )
    language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default=LANGUAGE_KO,
        help_text='Document language'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_UPLOADED,
        db_index=True,
        help_text='Processing status'
    )

    # Metadata
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='File size in bytes'
    )
    file_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='File MIME type (e.g., application/pdf)'
    )
    page_count = models.IntegerField(
        null=True,
        blank=True,
        help_text='Number of pages (for PDFs)'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if processing failed'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['doc_type', 'status']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_doc_type_display()})"

    @property
    def is_processing_complete(self):
        """Check if document has been fully processed"""
        return self.status == self.STATUS_EMBEDDED

    @property
    def chunk_count(self):
        """Get number of chunks for this document"""
        return self.chunks.count()


class DocumentChunk(models.Model):
    """
    DocumentChunk model for storing text chunks of a document

    Used for vector embedding and RAG retrieval
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks',
        help_text='Parent document'
    )
    chunk_index = models.IntegerField(
        help_text='Sequential index of chunk within document'
    )
    text = models.TextField(
        help_text='Chunk text content'
    )

    # Position metadata
    start_offset = models.IntegerField(
        null=True,
        blank=True,
        help_text='Starting character position in original document'
    )
    end_offset = models.IntegerField(
        null=True,
        blank=True,
        help_text='Ending character position in original document'
    )
    page_number = models.IntegerField(
        null=True,
        blank=True,
        help_text='Page number (for PDFs)'
    )

    # Vector DB reference
    embedding_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='ID in vector database (ChromaDB/Qdrant)'
    )

    # Metadata
    token_count = models.IntegerField(
        null=True,
        blank=True,
        help_text='Approximate token count for this chunk'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'document_chunks'
        ordering = ['document', 'chunk_index']
        unique_together = [['document', 'chunk_index']]
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
            models.Index(fields=['embedding_id']),
        ]

    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"

    @property
    def is_embedded(self):
        """Check if this chunk has been embedded in vector DB"""
        return bool(self.embedding_id)
