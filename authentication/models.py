from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    """Extended user profile for document analyzer"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    
    # Usage limits
    daily_upload_limit = models.IntegerField(default=30)
    monthly_upload_limit = models.IntegerField(default=500)
    
    # Preferences
    auto_classify = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} Profile"

class UserSession(models.Model):
    """Track user sessions and activity"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.session_key[:8]}..."