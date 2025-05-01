from django.contrib import admin
from .models import Invoice, RoyaltyPayment


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'period_start', 'period_end', 'amount', 'status', 'paid_at')
    list_filter = ('status',)
    search_fields = ('user__email',)
    raw_id_fields = ('user',)
    date_hierarchy = 'period_start'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RoyaltyPayment)
class RoyaltyPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'rights_owner', 'period_start', 'period_end', 'amount', 'status', 'paid_at')
    list_filter = ('status',)
    search_fields = ('rights_owner__email',)
    raw_id_fields = ('rights_owner',)
    date_hierarchy = 'period_start'
    readonly_fields = ('created_at', 'updated_at')
