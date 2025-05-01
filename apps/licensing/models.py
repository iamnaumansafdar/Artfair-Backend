from django.db import models
from apps.core.models import SoftDeleteBaseModel
from django.conf import settings

class License(SoftDeleteBaseModel):
    """Tracks licensing agreements between rights owners and licensees"""
    rights_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='issued_licenses')
    licensee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='received_licenses')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    terms = models.TextField()
    status = models.CharField(max_length=50)


class LicensedContent(SoftDeleteBaseModel):
    """Maps specific content to licenses"""
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name='licensed_content')
    media_file = models.ForeignKey('training_data.MediaFile', on_delete=models.PROTECT, related_name='licenses')
    access_type = models.CharField(max_length=50)
    restrictions = models.JSONField(default=dict)
