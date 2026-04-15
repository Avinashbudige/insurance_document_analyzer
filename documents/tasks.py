from celery import shared_task
from django.utils import timezone
from .models import Document, ProcessingLog

@shared_task(bind=True, max_retries=3)
def process_document_async(self, document_id):
    """Async task for document processing"""
    try:
        document = Document.objects.get(id=document_id)
        
        # Log processing start
        ProcessingLog.objects.create(
            document=document,
            step='initialization',
            status='started',
            message='Document processing started'
        )
        
        # Update status
        document.status = 'processing'
        document.save()
        
        # Here we'll integrate with LangGraph and Agents
        # For now, just simulate processing
        import time
        time.sleep(2)  # Simulate processing time
        
        # Update document with dummy results
        document.status = 'completed'
        document.processed_at = timezone.now()
        document.processing_time = 2.0
        document.confidence_score = 0.95
        document.entities = {
            'policy_number': 'POL-123456',
            'insured_name': 'John Doe',
            'claim_amount': 5000.00
        }
        document.save()
        
        # Log completion
        ProcessingLog.objects.create(
            document=document,
            step='completion',
            status='completed',
            message='Document processing completed successfully'
        )
        
        return {'status': 'success', 'document_id': str(document_id)}
        
    except Exception as exc:
        # Log error
        ProcessingLog.objects.create(
            document=document,
            step='error',
            status='failed',
            message=f'Processing failed: {str(exc)}'
        )
        
        document.status = 'failed'
        document.error_message = str(exc)
        document.save()
        
        raise self.retry(exc=exc, countdown=60, max_retries=3)