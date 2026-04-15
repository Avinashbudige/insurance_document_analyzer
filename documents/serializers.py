from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Document, ProcessingLog, ExtractedEntity, DocumentTag

class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    file_size_mb = serializers.SerializerMethodField()
    processing_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'user', 'title', 'file', 'file_size', 'file_size_mb',
            'page_count', 'document_type', 'confidence_score', 'status',
            'uploaded_at', 'processed_at', 'extracted_text', 'entities',
            'analysis_results', 'metadata', 'error_message', 'processing_time',
            'processing_status'
        ]
        read_only_fields = [
            'id', 'user', 'file_size', 'page_count', 'document_type',
            'confidence_score', 'status', 'uploaded_at', 'processed_at',
            'extracted_text', 'entities', 'analysis_results', 'metadata',
            'error_message', 'processing_time', 'processing_status'
        ]
    
    def get_file_size_mb(self, obj):
        return round(obj.file_size / (1024 * 1024), 2) if obj.file_size else 0
    
    def get_processing_status(self, obj):
        return {
            'status': obj.status,
            'progress': getattr(obj, 'processing_progress', 0),
            'current_step': getattr(obj, 'current_step', ''),
            'estimated_time': getattr(obj, 'estimated_time', 0)
        }

class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for document upload"""
    file = serializers.FileField(max_length=1000000)  # 50MB limit
    
    class Meta:
        model = Document
        fields = ['title', 'file']
    
    def validate_file(self, value):
        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Only PDF, JPEG, and PNG files are allowed.")
        
        # Validate file size (50MB)
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 50MB.")
        
        return value

class ExtractedEntitySerializer(serializers.ModelSerializer):
    """Serializer for extracted entities"""
    
    class Meta:
        model = ExtractedEntity
        fields = ['id', 'entity_type', 'value', 'confidence', 'page_number', 'coordinates', 'created_at']
        read_only_fields = ['id', 'created_at']

class ProcessingLogSerializer(serializers.ModelSerializer):
    """Serializer for processing logs"""
    
    class Meta:
        model = ProcessingLog
        fields = ['id', 'step', 'status', 'message', 'log_type', 'timestamp', 'duration']
        read_only_fields = ['id', 'timestamp']

class DocumentTagSerializer(serializers.ModelSerializer):
    """Serializer for document tags"""
    
    class Meta:
        model = DocumentTag
        fields = ['id', 'tag', 'created_at']
        read_only_fields = ['id', 'created_at']