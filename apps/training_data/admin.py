from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.template.defaultfilters import filesizeformat
from .models import MediaFile, AudioSegment, Speaker, Channel, ChannelMember
from django.utils import timezone
from django.urls import path
from django.shortcuts import render
from .tasks import test_task
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()
from .services import QueueProcessService


def run_test_celery(modeladmin, request, queryset):
    # Call the test task asynchronously.
    result = test_task.delay()
    # Display the Celery task id in the admin message.
    modeladmin.message_user(
        request,
        f"Test task queued with task id: {result.task_id}. Check worker logs for the result.",
        messages.SUCCESS
    )


run_test_celery.short_description = "Run Test Celery Task"


def queue_for_processing(modeladmin, request, queryset):
    """
    Generic action to queue items for processing
    """
    try:
        # Update status to 'processing' for selected items
        count = queryset.update(
            processing_status='processing',
            updated_at=timezone.now()
        )

        # Queue items for Celery task system
        QueueProcessService.queue_media_to_training_data(list(queryset))

        modeladmin.message_user(
            request,
            f'{count} items have been queued for processing.',
            messages.SUCCESS
        )
    except Exception as e:
        modeladmin.message_user(
            request,
            f'Error queueing items: {str(e)}',
            messages.ERROR
        )


queue_for_processing.short_description = "Queue selected items for processing"


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = (
    'id', 'original_filename', 'owner', 'file_type', 'formatted_file_size', 'processing_status', 'formatted_created_at',
    'display_linked_file', 'linked_file',)
    list_editable = ('linked_file',)
    list_filter = ('file_type', 'processing_status')
    search_fields = ('owner__email', 'md5_hash', 'original_filename')
    readonly_fields = ('created_at', 'updated_at', 'display_linked_file')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('owner', 'linked_file')

    # Remove add permission to hide the "ADD MEDIA FILE" button
    def has_add_permission(self, request):
        return False

    # Custom display functions: human readable file size.
    def formatted_file_size(self, obj):
        size = obj.safe_file_size  # safe_file_size should be defined as a property on your model
        if not size:
            return "-"
        return filesizeformat(size)
    formatted_file_size.short_description = "File Size"

    # Custom display functions: show associated file name on each row, if any.
    def display_linked_file(self, obj):
        linked_file = obj._get_linked_file()
        if not linked_file:
            return "-"
        return linked_file.full_file_name

    display_linked_file.short_description = "Linked File Name"

    # Custom display functions: make date and time into two separate lines to save room on the table.
    def formatted_created_at(self, obj):
        formatted_date = obj.created_at.strftime("%Y-%m-%d")
        formatted_time = obj.created_at.strftime("%H:%M")
        return format_html(
            '<div style="min-width: 100px;">{}<br>{}</div>',
            formatted_date,
            formatted_time
        )

    formatted_created_at.short_description = "Created At"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if settings.REMOTE_STATIC_FILES:
            # In remote mode, only show objects with a valid S3URL.
            qs = qs.filter(S3URL__isnull=False).exclude(S3URL="")
        # Only display files uploaded by user
        return qs

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('custom-page/', admin.site.admin_view(self.custom_page_view_1), name="custom_page"),
            path('custom-page1/', admin.site.admin_view(self.custom_page_view_2), name="custom_page1"),
        ]
        return custom_urls + urls

    def custom_page_view_1(self, request):
        users = User.objects.all().values("id", "email", "first_name", "last_name")
        return render(request, "admin/custom_page.html", {"users": users})

    def custom_page_view_2(self, request):
        context = {
        "remote_static_files": settings.REMOTE_STATIC_FILES  # Pass the flag into the template
        }
        return render(request, "admin/custom_page1.html", context)

    def process_video_view(self, request, pk):
        """
        This is a test admin panel view to test the processing pipeline for a single video/audio + caption pair.
        It does not trigger the celery flow.
        """
        video = MediaFile.objects.get(id=pk)
        if request.method == 'POST':
            selected_caption_id = request.POST.get('caption_file')
            try:
                #comment out the process_and_upload function
                # process_and_upload(pk, selected_caption_id)
                self.message_user(request,
                                  f"Processing tasks have been scheduled for  caption id: {request.POST.get('caption_file')}, vid id: {pk}")
            except ValueError as e:
                # Show the error message in the admin panel.
                self.message_user(request, str(e), messages.ERROR)

        caption_files = MediaFile.objects.filter(file_type='ass')
        default_caption_id = video.caption_file.id if video.caption_file else None
        return render(request, 'admin/process_video.html',
                      {'default_caption_id': default_caption_id, 'caption_files': caption_files,
                       'video_name': video.original_filename})

    def process_video(self, request, pk):
        obj = self.get_object(request, pk)
        # ... do something with obj ...
        self.message_user(request, "Custom action performed successfully.")

    actions = [run_test_celery, queue_for_processing]


@admin.register(AudioSegment)
class AudioSegmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_audio', "segment_file_local")
    list_filter = ('processing_status',)
    search_fields = (
        'id,'
        'original_filename',               
        'owner__email',                    
        'source_audio__original_filename'
    )
    raw_id_fields = ('source_audio', 'owner')
    # actions = [queue_for_processing]

    # def queue_transcription(self, request, queryset):
    #     try:
    #         # Update status for selected audio segments
    #         count = queryset.update(
    #             processing_status='processing',
    #             updated_at=timezone.now()
    #         )

    #         # Mock: Here you would queue transcription tasks
    #         self.message_user(
    #             request,
    #             f'{count} audio segments have been queued for transcription.',
    #             messages.SUCCESS
    #         )
    #     except Exception as e:
    #         self.message_user(
    #             request,
    #             f'Error queueing transcription: {str(e)}',
    #             messages.ERROR
    #         )

    # queue_transcription.short_description = "Queue audio for transcription"

    # # Add audio-specific action
    # actions = [queue_for_processing, queue_transcription]

    def get_queryset(self, request):
        return AudioSegment.objects.all()





@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'speaker_id', 'name', 'primary_language', 'dob', 'gender',
        'owner', 'created_at', 'updated_at'
    )
    list_filter = ('primary_language', 'gender', 'owner', 'created_at')
    search_fields = ('speaker_id', 'name', 'owner__email', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['owner', 'media_files']
    filter_horizontal = ('media_files',)
    fieldsets = (
        ("Speaker Info", {
            'fields': ('speaker_id', 'name', 'primary_language', 'dob', 'gender')
        }),
        ("Ownership & Files", {
            'fields': ('owner', 'media_files')
        }),
        ("Extra", {
            'fields': ('extra_metadata',)
        }),
        ("Timestamps", {
            'fields': ('created_at', 'updated_at')
        }),
    )
    

# ────────────────────────────────────────────────────────────
#  INLINE: members inside the Channel admin page
# ────────────────────────────────────────────────────────────
class ChannelMemberInline(admin.TabularInline):
    model = ChannelMember
    extra = 1                           # how many blank rows to show
    autocomplete_fields = ["user"]      # huge speed-up on big user tables
    classes = ["collapse"]              # collapsible section


# ────────────────────────────────────────────────────────────
#  CHANNEL
# ────────────────────────────────────────────────────────────
@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display    = (
        "title",
        "file_count",
        "member_count",
        "created_at",
    )
    search_fields   = ("title",)
    ordering        = ("title",)
    inlines         = [ChannelMemberInline]

    # nice counts in the list view
    def file_count(self, obj):
        return obj.channel_media_files.count()
    file_count.short_description = "Files"

    def member_count(self, obj):
        return obj.memberships.count()
    member_count.short_description = "Members"


# ────────────────────────────────────────────────────────────
#  CHANNEL MEMBER
# ────────────────────────────────────────────────────────────
@admin.register(ChannelMember)
class ChannelMemberAdmin(admin.ModelAdmin):
    list_display  = ("channel", "user_email", "role")
    list_filter   = ("role", "channel")
    search_fields = ("channel__title", "user__email")
    autocomplete_fields = ["channel", "user"]

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User email"
    