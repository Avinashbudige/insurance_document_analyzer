from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from .models import Document, ProcessingLog, ExtractedEntity, DocumentTag
from .serializers import (
    DocumentSerializer, DocumentUploadSerializer, 
    ExtractedEntitySerializer, ProcessingLogSerializer, DocumentTagSerializer
)
from .tasks import process_document_async
from .permissions import IsDocumentOwner

class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Document operations"""
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'document_type']
    search_fields = ['title', 'extracted_text']
    ordering_fields = ['uploaded_at', 'processed_at', 'title']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        """Filter documents by current user"""
        return Document.objects.filter(user=self.request.user).select_related('user').prefetch_related(
            'extracted_entities', 'processing_logs', 'tags'
        )
    
    def get_serializer_class(self):
        """Return different serializers for different actions"""
        if self.action == 'create':
            return DocumentUploadSerializer
        return DocumentSerializer
    
    def create(self, request, *args, **kwargs):
        """Upload and process document"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create document
        document = serializer.save(user=request.user)
        
        # Trigger async processing
        process_document_async.delay(document.id)
        
        # Return response
        response_serializer = DocumentSerializer(document, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get document processing status"""
        document = self.get_object()
        
        # Get latest processing log
        latest_log = document.processing_logs.last()
        
        return Response({
            'document_id': str(document.id),
            'status': document.status,
            'progress': getattr(document, 'processing_progress', 0),
            'current_step': getattr(document, 'current_step', ''),
            'estimated_time': getattr(document, 'estimated_time', 0),
            'error_message': document.error_message,
            'latest_log': ProcessingLogSerializer(latest_log).data if latest_log else None
        })
    
    @action(detail=True, methods=['get'])
    def analysis(self, request, pk=None):
        """Get document analysis results"""
        document = self.get_object()
        
        return Response({
            'document_id': str(document.id),
            'entities': ExtractedEntitySerializer(
                document.extracted_entities.all(), many=True
            ).data,
            'analysis_results': document.analysis_results,
            'confidence_score': document.confidence_score,
            'processing_time': document.processing_time,
            'processing_logs': ProcessingLogSerializer(
                document.processing_logs.all().order_by('-timestamp')[:10], 
                many=True
            ).data
        })
    
    @action(detail=True, methods=['post'])
    def retry_processing(self, request, pk=None):
        """Retry document processing"""
        document = self.get_object()
        
        if document.status not in ['failed', 'completed']:
            return Response(
                {'error': 'Document is not eligible for retry'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset status and trigger processing
        document.status = 'uploaded'
        document.error_message = ''
        document.save()
        
        process_document_async.delay(document.id)
        
        return Response({'message': 'Processing restarted'})
    
    @action(detail=True, methods=['get', 'post'])
    def tags(self, request, pk=None):
        """Get or add document tags"""
        document = self.get_object()
        
        if request.method == 'GET':
            tags = document.tags.all()
            return Response(DocumentTagSerializer(tags, many=True).data)
        
        elif request.method == 'POST':
            tag_name = request.data.get('tag', '').strip()
            if not tag_name:
                return Response(
                    {'error': 'Tag name is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            tag, created = DocumentTag.objects.get_or_create(
                document=document, tag=tag_name.lower()
            )
            
            return Response(
                DocumentTagSerializer(tag).data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
    
    @action(detail=True, methods=['delete'], url_path='tags/(?P<tag_name>[^/]+)')
    def remove_tag(self, request, pk=None, tag_name=None):
        """Remove a specific tag from document"""
        document = self.get_object()
        
        try:
            tag = document.tags.get(tag=tag_name)
            tag.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DocumentTag.DoesNotExist:
            return Response(
                {'error': 'Tag not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class ExtractedEntityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for extracted entities"""
    serializer_class = ExtractedEntitySerializer
    permission_classes = [IsAuthenticated, IsDocumentOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['entity_type', 'confidence']
    search_fields = ['value']
    
    def get_queryset(self):
        """Filter entities by user's documents"""
        return ExtractedEntity.objects.filter(
            document__user=self.request.user
        ).select_related('document')