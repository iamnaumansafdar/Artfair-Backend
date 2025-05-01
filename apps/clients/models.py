from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
import os
import hashlib
from apps.core.models imort BaseModel

class Client(BaseModel):
    """Model to represent clients in the system"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    s3_bucket_name = models.CharField(max_length=255, default='artfair-data')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']