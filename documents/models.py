from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Document(models.Model):
    """Main document model for storing PDF and processed data"""
    
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('archived', 'Archived'),
    ]
    
    DOCUMENT_TYPES = [
        ('claim', 'Claim Form'),
        ('policy', 'Policy Document'),
        ('invoice', 'Invoice'),
        ('medical_report', 'Medical Report'),
        ('correspondence', 'Correspondence'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/uploads/')
    file_size = models.BigIntegerField(default=0)  # in bytes
    page_count = models.IntegerField(default=0)
    
    # Classification
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, blank=True)
    confidence_score = models.FloatField(default=0.0)
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Extracted content
    extracted_text = models.TextField(blank=True)
    raw_text = models.TextField(blank=True)  # OCR output before cleaning
    
    # Analysis results (JSON fields for flexibility)
    entities = models.JSONField(default=dict, blank=True)
    analysis_results = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Processing logs
    error_message = models.TextField(blank=True)
    processing_time = models.FloatField(default=0.0)  # in seconds
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['document_type']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    @property
    def file_extension(self):
        return self.file.name.split('.')[-1].lower() if self.file else ''

class ProcessingLog(models.Model):
    """Track processing steps and their status"""
    
    LOG_TYPES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('debug', 'Debug'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='processing_logs')
    step = models.CharField(max_length=100)  # e.g., 'ocr_processing', 'entity_extraction'
    status = models.CharField(max_length=20)  # e.g., 'started', 'completed', 'failed'
    message = models.TextField()
    log_type = models.CharField(max_length=10, choices=LOG_TYPES, default='info')
    timestamp = models.DateTimeField(auto_now_add=True)
    duration = models.FloatField(default=0.0)  # in seconds
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['document', 'step']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.document.title} - {self.step} - {self.status}"

class ExtractedEntity(models.Model):
    """Store extracted entities from documents"""
    
    ENTITY_TYPES = [
        ('policy_number', 'Policy Number'),
        ('claim_number', 'Claim Number'),
        ('insured_name', 'Insured Name'),
        ('date_of_loss', 'Date of Loss'),
        ('claim_amount', 'Claim Amount'),
        ('coverage_type', 'Coverage Type'),
        ('insurance_company', 'Insurance Company'),
        ('address', 'Address'),
        ('phone', 'Phone Number'),
        ('email', 'Email'),
        ('other', 'Other'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='extracted_entities')
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES)
    value = models.TextField()
    confidence = models.FloatField(default=0.0)
    page_number = models.IntegerField(null=True, blank=True)
    coordinates = models.JSONField(default=dict, blank=True)  # bbox coordinates
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['entity_type']
        indexes = [
            models.Index(fields=['document', 'entity_type']),
            models.Index(fields=['entity_type', 'value']),
        ]
    
    def __str__(self):
        return f"{self.document.title} - {self.entity_type}: {self.value}"

class DocumentTag(models.Model):
    """Tags for categorizing and searching documents"""
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='tags')
    tag = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['document', 'tag']
        ordering = ['tag']
    
    def __str__(self):
        return f"{self.document.title} - {self.tag}"