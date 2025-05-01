from django.db import models
from apps.core.models import BaseModel
from django.conf import settings


# Create your models here.
class Invoice(BaseModel):
    """Tracks invoices for licensees"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50)
    paid_at = models.DateTimeField(null=True, blank=True)


class RoyaltyPayment(BaseModel):
    """Tracks royalty payments to rights owners"""
    rights_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50)
    paid_at = models.DateTimeField(null=True, blank=True)
