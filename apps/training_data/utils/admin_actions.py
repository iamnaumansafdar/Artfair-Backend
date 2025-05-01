from django.contrib import admin
from django.contrib import messages
from ..tasks import extract_metadata, convert_video_to_audio, process_audio_segments
from ..exceptions import MetadataExtractionError

def queue_metadata_extraction(modeladmin, request, queryset):
    try:
        task_count = 0
        for video in queryset:
            if not video.metadata:
                extract_metadata.delay(video.id)
                task_count += 1
        if task_count == 0:
            raise MetadataExtractionError("No videos required metadata extraction.")
        messages.success(request, f"Metadata extraction tasks queued for {task_count} videos.")
    except MetadataExtractionError as e:
        messages.warning(request, str(e))
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")

queue_metadata_extraction.short_description = "Extract metadata for selected videos"



def queue_convert_video_to_audio(modeladmin, request, queryset):
    try:
        task_count = 0
        for video in queryset:
                convert_video_to_audio.delay(video.id)
                task_count += 1
        if task_count == 0:
            raise MetadataExtractionError("No videos required metadata extraction.")
        messages.success(request, f"Audio extraction tasks queued for {task_count} videos.")
    except MetadataExtractionError as e:
        messages.warning(request, str(e))
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")

queue_convert_video_to_audio.short_description = "Extract Audio metadata for selected videos"



@admin.action(description="Process audio segments for selected videos")
def process_audio_segments_action(modeladmin, request, queryset):
    try:
        task_count = 0
        for video in queryset:
            captions_path = video.metadata.get("captions_csv_path")
            if captions_path:
                process_audio_segments.delay(video.id, captions_path)
                task_count += 1
        if task_count == 0:
            raise MetadataExtractionError("No videos required metadata extraction.")
        messages.success(request, "Audio segmentation tasks queued.")
    except MetadataExtractionError as e:
        messages.warning(request, str(e))
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")


