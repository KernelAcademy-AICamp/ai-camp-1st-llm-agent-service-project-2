from rest_framework import serializers
from .models import Document, DocumentChunk


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


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""

    # Read-only fields
    chunk_count = serializers.IntegerField(read_only=True)
    is_processing_complete = serializers.BooleanField(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

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
            'file_size',
            'file_type',
            'page_count',
            'error_message',
            'chunk_count',
            'is_processing_complete',
            'chunks',
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
            'chunks',
            'created_at',
            'updated_at',
        ]
