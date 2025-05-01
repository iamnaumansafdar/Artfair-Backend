from django.contrib import admin
from .models import License, LicensedContent


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'rights_owner', 'licensee', 'start_date', 'end_date', 'status')
    list_filter = ('status',)
    search_fields = ('rights_owner__email', 'licensee__email', 'terms')
    raw_id_fields = ('rights_owner', 'licensee')
    date_hierarchy = 'start_date'

    def get_queryset(self, request):
        return License.objects.all()


@admin.register(LicensedContent)
class LicensedContentAdmin(admin.ModelAdmin):
    list_display = ('id', 'license', 'media_file', 'access_type')
    list_filter = ('access_type',)
    search_fields = ('license__rights_owner__email', 'license__licensee__email')
    raw_id_fields = ('license', 'media_file')

    def get_queryset(self, request):
        return LicensedContent.objects.all()