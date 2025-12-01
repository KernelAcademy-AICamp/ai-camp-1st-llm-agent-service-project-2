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

    # Analysis status (for auto-analysis pipeline)
    ANALYSIS_PENDING = 'pending'
    ANALYSIS_SUMMARIZING = 'summarizing'
    ANALYSIS_EXTRACTING_CLAUSES = 'extracting_clauses'
    ANALYSIS_ANALYZING_RISK = 'analyzing_risk'
    ANALYSIS_COMPLETED = 'completed'
    ANALYSIS_FAILED = 'failed'
    ANALYSIS_NONE = 'none'

    ANALYSIS_STATUS_CHOICES = [
        (ANALYSIS_NONE, 'No Analysis'),
        (ANALYSIS_PENDING, 'Pending'),
        (ANALYSIS_SUMMARIZING, 'Summarizing'),
        (ANALYSIS_EXTRACTING_CLAUSES, 'Extracting Clauses'),
        (ANALYSIS_ANALYZING_RISK, 'Analyzing Risk'),
        (ANALYSIS_COMPLETED, 'Completed'),
        (ANALYSIS_FAILED, 'Failed'),
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
    analysis_status = models.CharField(
        max_length=30,
        choices=ANALYSIS_STATUS_CHOICES,
        default=ANALYSIS_NONE,
        db_index=True,
        help_text='Analysis pipeline status'
    )
    analysis_error = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if analysis failed'
    )

    # Metadata
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='File size in bytes'
    )
    file_type = models.CharField(
        max_length=100,
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
        help_text='ID in vector database (Qdrant)'
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


class Summary(models.Model):
    """
    Summary model for storing AI-generated document summaries

    Supports both global document summaries and section-level summaries
    """

    # Summary types
    SUMMARY_TYPE_GLOBAL = 'GLOBAL'
    SUMMARY_TYPE_SECTION = 'SECTION'

    SUMMARY_TYPE_CHOICES = [
        (SUMMARY_TYPE_GLOBAL, 'Global Summary'),
        (SUMMARY_TYPE_SECTION, 'Section Summary'),
    ]

    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='summaries',
        help_text='Associated document'
    )
    llm_model = models.CharField(
        max_length=100,
        help_text='LLM model used for generation (e.g., gpt-4, claude-3-opus)'
    )
    summary_type = models.CharField(
        max_length=20,
        choices=SUMMARY_TYPE_CHOICES,
        default=SUMMARY_TYPE_GLOBAL,
        help_text='Type of summary'
    )
    content = models.TextField(
        help_text='Summary text content'
    )
    meta = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional metadata (section_title, token_count, etc.)'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'summaries'
        ordering = ['-created_at']
        verbose_name_plural = 'Summaries'
        indexes = [
            models.Index(fields=['document', '-created_at']),
            models.Index(fields=['summary_type']),
        ]

    def __str__(self):
        return f"{self.document.title} - {self.get_summary_type_display()} ({self.llm_model})"


class KeyClause(models.Model):
    """
    KeyClause model for storing extracted key clauses from contracts/documents

    Captures important clauses with importance scoring
    """

    # Clause types (common contract clauses)
    CLAUSE_TYPE_PAYMENT = 'PAYMENT'
    CLAUSE_TYPE_TERMINATION = 'TERMINATION'
    CLAUSE_TYPE_LIABILITY = 'LIABILITY'
    CLAUSE_TYPE_CONFIDENTIALITY = 'CONFIDENTIALITY'
    CLAUSE_TYPE_DISPUTE = 'DISPUTE'
    CLAUSE_TYPE_WARRANTY = 'WARRANTY'
    CLAUSE_TYPE_INDEMNITY = 'INDEMNITY'
    CLAUSE_TYPE_FORCE_MAJEURE = 'FORCE_MAJEURE'
    CLAUSE_TYPE_INTELLECTUAL_PROPERTY = 'INTELLECTUAL_PROPERTY'
    CLAUSE_TYPE_OTHER = 'OTHER'

    CLAUSE_TYPE_CHOICES = [
        (CLAUSE_TYPE_PAYMENT, 'Payment Terms'),
        (CLAUSE_TYPE_TERMINATION, 'Termination'),
        (CLAUSE_TYPE_LIABILITY, 'Liability'),
        (CLAUSE_TYPE_CONFIDENTIALITY, 'Confidentiality'),
        (CLAUSE_TYPE_DISPUTE, 'Dispute Resolution'),
        (CLAUSE_TYPE_WARRANTY, 'Warranty'),
        (CLAUSE_TYPE_INDEMNITY, 'Indemnification'),
        (CLAUSE_TYPE_FORCE_MAJEURE, 'Force Majeure'),
        (CLAUSE_TYPE_INTELLECTUAL_PROPERTY, 'Intellectual Property'),
        (CLAUSE_TYPE_OTHER, 'Other'),
    ]

    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='key_clauses',
        help_text='Associated document'
    )
    clause_type = models.CharField(
        max_length=50,
        choices=CLAUSE_TYPE_CHOICES,
        default=CLAUSE_TYPE_OTHER,
        help_text='Type of clause'
    )
    title = models.CharField(
        max_length=500,
        help_text='Clause title or heading'
    )
    content = models.TextField(
        help_text='Clause text content'
    )
    importance_score = models.IntegerField(
        default=50,
        help_text='Importance score (0-100)'
    )
    llm_model = models.CharField(
        max_length=100,
        help_text='LLM model used for extraction'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'key_clauses'
        ordering = ['-importance_score', '-created_at']
        indexes = [
            models.Index(fields=['document', '-importance_score']),
            models.Index(fields=['clause_type']),
        ]

    def __str__(self):
        return f"{self.document.title} - {self.title} ({self.importance_score})"


class RiskAnalysisResult(models.Model):
    """
    RiskAnalysisResult model for storing AI-generated risk analysis of contracts/documents

    Identifies potential risks, red flags, and assigns risk scores
    """

    # Risk severity levels
    SEVERITY_CRITICAL = 'CRITICAL'
    SEVERITY_HIGH = 'HIGH'
    SEVERITY_MEDIUM = 'MEDIUM'
    SEVERITY_LOW = 'LOW'
    SEVERITY_INFO = 'INFO'

    SEVERITY_CHOICES = [
        (SEVERITY_CRITICAL, 'Critical'),
        (SEVERITY_HIGH, 'High'),
        (SEVERITY_MEDIUM, 'Medium'),
        (SEVERITY_LOW, 'Low'),
        (SEVERITY_INFO, 'Informational'),
    ]

    # Risk categories
    CATEGORY_LEGAL = 'LEGAL'
    CATEGORY_FINANCIAL = 'FINANCIAL'
    CATEGORY_COMPLIANCE = 'COMPLIANCE'
    CATEGORY_OPERATIONAL = 'OPERATIONAL'
    CATEGORY_REPUTATIONAL = 'REPUTATIONAL'
    CATEGORY_OTHER = 'OTHER'

    CATEGORY_CHOICES = [
        (CATEGORY_LEGAL, 'Legal Risk'),
        (CATEGORY_FINANCIAL, 'Financial Risk'),
        (CATEGORY_COMPLIANCE, 'Compliance Risk'),
        (CATEGORY_OPERATIONAL, 'Operational Risk'),
        (CATEGORY_REPUTATIONAL, 'Reputational Risk'),
        (CATEGORY_OTHER, 'Other'),
    ]

    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='risk_analyses',
        help_text='Associated document'
    )
    overall_risk_score = models.IntegerField(
        default=0,
        help_text='Overall risk score (0-100, higher is riskier)'
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_LOW,
        help_text='Overall risk severity level'
    )
    risk_items = models.JSONField(
        default=list,
        help_text='List of identified risk items with details'
    )
    recommendations = models.JSONField(
        default=list,
        help_text='List of recommendations to mitigate risks'
    )
    summary = models.TextField(
        help_text='Summary of risk analysis'
    )
    llm_model = models.CharField(
        max_length=100,
        help_text='LLM model used for analysis'
    )
    meta = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional metadata (token_count, analysis_time, etc.)'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'risk_analysis_results'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', '-created_at']),
            models.Index(fields=['severity', '-overall_risk_score']),
        ]

    def __str__(self):
        return f"{self.document.title} - Risk Analysis ({self.severity}, Score: {self.overall_risk_score})"

    @property
    def is_high_risk(self):
        """Check if this is a high or critical risk"""
        return self.severity in [self.SEVERITY_CRITICAL, self.SEVERITY_HIGH]

    @property
    def risk_item_count(self):
        """Get number of risk items identified"""
        return len(self.risk_items) if isinstance(self.risk_items, list) else 0


class CaseAnalysis(models.Model):
    """
    CaseAnalysis model for storing AI-generated case analysis results

    Replaces the legacy Case.analysis JSONField with a proper model structure
    Captures case parties, issues, key dates, related precedents, and next steps
    """

    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='case_analysis',
        help_text='Associated document (must be doc_type=CASE)'
    )
    suggested_case_name = models.CharField(
        max_length=255,
        help_text='AI-suggested case name based on content'
    )
    document_types = models.JSONField(
        default=list,
        help_text='List of document types identified (e.g., ["판결문", "소장", "계약서"])'
    )
    parties = models.JSONField(
        default=dict,
        help_text='Parties involved (e.g., {"원고": "홍길동", "피고": "김철수"})'
    )
    key_dates = models.JSONField(
        default=dict,
        help_text='Important dates (e.g., {"사고일": "2024-01-15", "제소일": "2024-02-01"})'
    )
    issues = models.JSONField(
        default=list,
        help_text='Key legal issues identified'
    )
    related_precedents = models.JSONField(
        default=list,
        help_text='Related precedents from RAG search'
    )
    suggested_next_steps = models.JSONField(
        default=list,
        help_text='AI-suggested next steps for the case'
    )
    scenario = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        help_text='Case scenario analysis with confidence scores'
    )
    llm_model = models.CharField(
        max_length=100,
        help_text='LLM model used for analysis'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'case_analyses'
        ordering = ['-created_at']
        verbose_name = 'Case Analysis'
        verbose_name_plural = 'Case Analyses'
        indexes = [
            models.Index(fields=['document']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.suggested_case_name} - Analysis"

    @property
    def party_count(self):
        """Get number of parties involved"""
        return len(self.parties) if isinstance(self.parties, dict) else 0

    @property
    def issue_count(self):
        """Get number of issues identified"""
        return len(self.issues) if isinstance(self.issues, list) else 0

    @property
    def has_precedents(self):
        """Check if related precedents were found"""
        return bool(self.related_precedents)
