from django.contrib import admin
from .models import AccessLog, ProcessingJob, Usage


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'media_file', 'access_type', 'timestamp', 'ip_address')
    list_filter = ('access_type',)
    search_fields = ('user__email', 'ip_address', 'user_agent')
    raw_id_fields = ('user', 'media_file')
    date_hierarchy = 'timestamp'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'media_file', 'job_type', 'status', 'started_at', 'completed_at')
    list_filter = ('job_type', 'status')
    search_fields = ('media_file__file_path', 'error_message')
    raw_id_fields = ('media_file',)
    date_hierarchy = 'started_at'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Usage)
class UsageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'license', 'period_start', 'period_end', 'access_count', 'data_transferred')
    list_filter = ('access_count', 'data_transferred')
    search_fields = ('user__email',)
    raw_id_fields = ('user', 'license')
    date_hierarchy = 'period_start'
    readonly_fields = ('created_at', 'updated_at')