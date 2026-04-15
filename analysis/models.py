from django.db import models
from django.contrib.auth.models import User
from apps.documents.models import Document

class AnalysisResult(models.Model):
    """Store detailed analysis results"""
    
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='detailed_analysis')
    risk_score = models.FloatField(default=0.0)
    confidence_score = models.FloatField(default=0.0)
    
    # Analysis metrics
    completeness_score = models.FloatField(default=0.0)
    accuracy_score = models.FloatField(default=0.0)
    fraud_indicators = models.JSONField(default=list, blank=True)
    
    # Recommendations
    recommendations = models.JSONField(default=list, blank=True)
    required_actions = models.JSONField(default=list, blank=True)
    
    # Processing details
    processing_time = models.FloatField(default=0.0)
    agent_version = models.CharField(max_length=20, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analysis for {self.document.title}"

class RuleExecution(models.Model):
    """Track rule engine executions"""
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='rule_executions')
    rule_name = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=50)  # e.g., 'validation', 'extraction', 'risk_assessment'
    status = models.CharField(max_length=20)  # e.g., 'passed', 'failed', 'skipped'
    result = models.JSONField(default=dict, blank=True)
    execution_time = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', 'rule_type']),
            models.Index(fields=['rule_name']),
        ]
    
    def __str__(self):
        return f"{self.document.title} - {self.rule_name} - {self.status}"