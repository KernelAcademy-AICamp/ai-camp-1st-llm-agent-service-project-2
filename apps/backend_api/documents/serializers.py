from rest_framework import serializers
from .models import Document, DocumentChunk, Summary, KeyClause, RiskAnalysisResult, CaseAnalysis


class DocumentChunkSerializer(serializers.ModelSerializer):
    """Serializer for DocumentChunk model"""

    class Meta:
        model = DocumentChunk
        fields = [
            'id',
            'document',
            'chunk_index',
            'text',
            'start_offset',
            'end_offset',
            'page_number',
            'embedding_id',
            'token_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CaseAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for CaseAnalysis model"""

    document_title = serializers.CharField(source='document.title', read_only=True)
    party_count = serializers.IntegerField(read_only=True)
    issue_count = serializers.IntegerField(read_only=True)
    has_precedents = serializers.BooleanField(read_only=True)

    class Meta:
        model = CaseAnalysis
        fields = [
            'id',
            'document',
            'document_title',
            'suggested_case_name',
            'document_types',
            'parties',
            'party_count',
            'key_dates',
            'issues',
            'issue_count',
            'related_precedents',
            'has_precedents',
            'suggested_next_steps',
            'scenario',
            'llm_model',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""

    # Read-only fields
    chunk_count = serializers.IntegerField(read_only=True)
    is_processing_complete = serializers.BooleanField(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    analysis_status_display = serializers.CharField(source='get_analysis_status_display', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id',
            'user',
            'user_email',
            'title',
            'doc_type',
            'source_type',
            'original_file',
            'language',
            'status',
            'analysis_status',
            'analysis_status_display',
            'analysis_error',
            'file_size',
            'file_type',
            'page_count',
            'error_message',
            'chunk_count',
            'is_processing_complete',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'file_size',
            'file_type',
            'page_count',
            'error_message',
            'chunk_count',
            'is_processing_complete',
            'analysis_status',
            'analysis_status_display',
            'analysis_error',
            'created_at',
            'updated_at',
        ]

    def validate_original_file(self, value):
        """
        Validate file size and extension
        """
        if not value:
            return value

        # Check file size (10MB = 10 * 1024 * 1024 bytes)
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f'File size must be less than 10MB. Current size: {value.size / (1024 * 1024):.2f}MB'
            )

        # Check file extension
        allowed_extensions = ['.pdf', '.docx', '.txt']
        file_name = value.name.lower()
        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f'File extension not allowed. Allowed extensions: {", ".join(allowed_extensions)}'
            )

        return value


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for document upload"""

    original_file = serializers.FileField(required=True)

    class Meta:
        model = Document
        fields = [
            'title',
            'doc_type',
            'language',
            'original_file',
        ]

    def validate_original_file(self, value):
        """
        Validate file size and extension
        """
        # Check file size (10MB = 10 * 1024 * 1024 bytes)
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f'File size must be less than 10MB. Current size: {value.size / (1024 * 1024):.2f}MB'
            )

        # Check file extension
        allowed_extensions = ['.pdf', '.docx', '.txt']
        file_name = value.name.lower()
        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f'File extension not allowed. Allowed extensions: {", ".join(allowed_extensions)}'
            )

        return value

    def create(self, validated_data):
        """
        Create a new document with file metadata
        """
        file = validated_data['original_file']

        # Extract file metadata
        validated_data['file_size'] = file.size
        validated_data['file_type'] = file.content_type
        validated_data['source_type'] = Document.SOURCE_UPLOAD
        validated_data['status'] = Document.STATUS_UPLOADED

        # Set user from context
        validated_data['user'] = self.context['request'].user

        return super().create(validated_data)


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Serializer for document detail with chunks"""

    chunks = DocumentChunkSerializer(many=True, read_only=True)
    chunk_count = serializers.IntegerField(read_only=True)
    is_processing_complete = serializers.BooleanField(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    case_analysis = CaseAnalysisSerializer(read_only=True)
    analysis_status_display = serializers.CharField(source='get_analysis_status_display', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id',
            'user',
            'user_email',
            'title',
            'doc_type',
            'source_type',
            'original_file',
            'language',
            'status',
            'analysis_status',
            'analysis_status_display',
            'analysis_error',
            'content',  # 원문 텍스트
            'file_size',
            'file_type',
            'page_count',
            'error_message',
            'chunk_count',
            'is_processing_complete',
            'chunks',
            'case_analysis',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'file_size',
            'file_type',
            'page_count',
            'error_message',
            'content',  # 원문 텍스트
            'chunk_count',
            'is_processing_complete',
            'analysis_status',
            'analysis_status_display',
            'analysis_error',
            'chunks',
            'case_analysis',
            'created_at',
            'updated_at',
        ]


class SummarySerializer(serializers.ModelSerializer):
    """Serializer for Summary model"""

    document_title = serializers.CharField(source='document.title', read_only=True)

    class Meta:
        model = Summary
        fields = [
            'id',
            'document',
            'document_title',
            'llm_model',
            'summary_type',
            'content',
            'meta',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class KeyClauseSerializer(serializers.ModelSerializer):
    """Serializer for KeyClause model"""

    document_title = serializers.CharField(source='document.title', read_only=True)
    clause_type_display = serializers.CharField(source='get_clause_type_display', read_only=True)

    class Meta:
        model = KeyClause
        fields = [
            'id',
            'document',
            'document_title',
            'clause_type',
            'clause_type_display',
            'title',
            'content',
            'importance_score',
            'llm_model',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_importance_score(self, value):
        """Validate importance score is between 0-100"""
        if value < 0 or value > 100:
            raise serializers.ValidationError('Importance score must be between 0 and 100')
        return value


class RiskAnalysisResultSerializer(serializers.ModelSerializer):
    """Serializer for RiskAnalysisResult model"""

    document_title = serializers.CharField(source='document.title', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    risk_item_count = serializers.IntegerField(read_only=True)
    is_high_risk = serializers.BooleanField(read_only=True)

    class Meta:
        model = RiskAnalysisResult
        fields = [
            'id',
            'document',
            'document_title',
            'overall_risk_score',
            'severity',
            'severity_display',
            'risk_items',
            'recommendations',
            'summary',
            'llm_model',
            'meta',
            'risk_item_count',
            'is_high_risk',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_overall_risk_score(self, value):
        """Validate risk score is between 0-100"""
        if value < 0 or value > 100:
            raise serializers.ValidationError('Risk score must be between 0 and 100')
        return value

    def to_representation(self, instance):
        """
        Override to transform risk_items to frontend format.
        Frontend RiskItem: category, title, description, severity, score, clause_reference
        """
        data = super().to_representation(instance)

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

        # Transform risk_items to frontend format if needed
        risk_items = data.get('risk_items', [])
        if risk_items:
            transformed_items = []
            for i, risk in enumerate(risk_items, 1):
                # Check if already in new format (has 'category' field)
                if 'category' in risk:
                    transformed_items.append(risk)
                else:
                    # Transform from old format to new format
                    risk_type = risk.get('risk_type', 'OTHER')
                    severity = risk.get('severity', 'MEDIUM')
                    description = risk.get('description', '')
                    clause_ref = risk.get('clause_reference', '')

                    # Generate title
                    if clause_ref:
                        title = f"{clause_ref} 관련 리스크"
                    else:
                        title = f"{risk_type} 리스크 #{i}"

                    transformed_items.append({
                        'category': risk_type,
                        'title': title,
                        'description': description,
                        'severity': severity,
                        'score': severity_to_score(severity),
                        'clause_reference': clause_ref,
                        # Legacy fields for compatibility
                        'risk_type': risk_type,
                        'recommendation': risk.get('recommendation', '')
                    })
            data['risk_items'] = transformed_items

        return data