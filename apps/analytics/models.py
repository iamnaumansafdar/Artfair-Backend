from django.db import models
from apps.core.models import BaseModel
from django.conf import settings

# Create your models here.
class AccessLog(BaseModel):
    """Tracks all data access events"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    media_file = models.ForeignKey('training_data.MediaFile', on_delete=models.PROTECT)
    access_type = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()


class ProcessingJob(BaseModel):
    """Tracks media processing tasks"""
    media_file = models.ForeignKey('training_data.MediaFile', on_delete=models.PROTECT)
    job_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)


class Usage(BaseModel):
    """Aggregated usage metrics for billing"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    license = models.ForeignKey('licensing.License', on_delete=models.PROTECT, null=True)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    access_count = models.IntegerField(default=0)
    data_transferred = models.BigIntegerField(default=0)
    metrics = models.JSONField(default=dict)