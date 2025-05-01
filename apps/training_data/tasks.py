# tasks.py
from celery import shared_task
import os, re
import pandas as pd
from io import BytesIO
from apps.users.models import CustomUser
from .models import MediaFile, AudioSegment, local_storage
from conf.settings import BASE_DIR
from django.core.files.storage import default_storage
from django.conf import settings
import tempfile
import boto3
import glob
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
from .complete_task_email import SuccessEmailTask
from pathlib import Path
from django.conf import settings
from .utils import (
    convert_video_to_audio,
    process_audio,
    create_audio_clips,
    split_dataframe,
    upload_to_huggingface,
    convert_subtitles_to_metadata,
    split_dataframe,
    get_video_duration_seconds,
    format_duration
    
)

# Hugging Face Split names
TRAIN = "train"
TEST = "test"
VAL = "val"

@shared_task(bind=True, base=SuccessEmailTask)
def test_task(self):
    # This task simply returns a message.
    return "Celery is working!"

@shared_task
def add(x, y):
    return x + y

# ------------------------------------------------------------------
# 1)  COMBINE PER‑VIDEO CSVs AND WRITE THE FINAL ONE IN THE *SAME* FOLDER
# ------------------------------------------------------------------
@shared_task(bind=True, routing_key="default")
def compile_dataset(self, channel_id: int,
                    train_ratio: int = 70,
                    test_ratio: int = 15,
                    validate_ratio: int = 15) -> str:
    """
    Combine all .csv files in uploads/<channel_id>/mediafile,
    add a train/test/val split, and write
    uploads/<channel_id>/mediafile/final_output.csv
    (returns the *full path* of that file).
    """
    root = settings.UPLOADS_ROOT
    media_dir = Path(root)  / str(channel_id) / "mediafile"
    # csv_paths = list(media_dir.glob("*.csv"))
    csv_paths = [p for p in media_dir.glob("*.csv")
            if "audio_path" in pd.read_csv(p, nrows=1).columns]


    if not csv_paths:
        raise FileNotFoundError(f"No CSV files found in {media_dir}")

    df = pd.concat(
        (pd.read_csv(p, encoding="utf-8-sig", on_bad_lines="skip") for p in csv_paths),
        ignore_index=True,
    )

    df = split_dataframe(df, train_ratio, test_ratio, validate_ratio)

    required = [
        "speaker_name", "caption_text", "channel_id", "video_name",
        "speaker_id", "full_path", "audio_path", "split",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Columns missing: {missing}")

    out_path = media_dir / "final_output.csv"
    df[required].to_csv(out_path, index=False, encoding="utf-8-sig")

    logging.getLogger(__name__).info(f"Combined CSV saved → {out_path}")
    return str(out_path)      # return *only* the path




@shared_task(bind=True, routing_key="video_processing")
def process_video_file(self, media_file_id):
    """Process video file - convert to audio"""
    try:
        video_file = MediaFile.objects.get(id=media_file_id)
        video_file.processing_status = 'processing'
        video_file.save()
        
        
        # First, try to get the local file path.
        try:
            file_path = video_file.file.path
            print("Local file path found:", file_path)
        except Exception as e:
            print("Local file access failed:", e)
            # If the .path attribute isn't available, try downloading from S3.
            try:
                s3_client = boto3.client('s3', region_name=settings.AWS_S3_REGION)
                bucket = settings.AWS_STORAGE_BUCKET_NAME
                file_key = video_file.file.name  # This is the S3 key.
                tmp_file = tempfile.NamedTemporaryFile(delete=False)
                s3_client.download_file(bucket, file_key, tmp_file.name)
                file_path = tmp_file.name
                print("File downloaded from S3 to temporary path:", file_path)
            except Exception as s3_error:
                print("S3 download failed:", s3_error)
                file_path = None

        # If we have a file path, extract duration; otherwise, save None.
        if file_path:
            duration_seconds = get_video_duration_seconds(file_path)
            print(f"Duration in seconds: {duration_seconds}")
            duration_formatted = format_duration(duration_seconds)
            print(f"Formatted duration: {duration_formatted}")
            video_file.video_duration = duration_formatted
        else:
            print("No file path available; setting duration to None.")
            video_file.video_duration = None
        
        video_file.save()
        
        

        convert_video_to_audio(video_file.id)
        video_file.refresh_from_db()
        video_file.processing_status = 'completed'
        video_file.save()
        # Verify the file was saved
        if not video_file.processed_audio_file:
            raise Exception("Processed audio file was not created")
    except Exception as e:
        video_file.processing_status = 'failed'
        video_file.metadata['error'] = str(e)
        video_file.save()
        raise

def get_user_metadata(client_id):
    all_csvs = []
    user = CustomUser.objects.get(id=client_id)
    media_files = MediaFile.objects.filter(
        owner=user,
        is_source_file=True,
         _metadata_file__isnull=False,
    ).exclude(_metadata_file="")

    for media_file in media_files:
        try:
            with media_file.metadata_file.open("rb") as f:
                content = f.read()
                data = pd.read_csv(
                    BytesIO(content),
                    encoding='utf-8-sig',
                    on_bad_lines='skip'
                )
                all_csvs.append(data)
        except Exception as e:
            logger.error(f"Failed to read {media_file.metadata_file.name}: {e}")
            continue  # Skip corrupt files

    # Combine all metadata into one dataframe
    if all_csvs:
        return pd.concat(all_csvs, ignore_index=True)
    return pd.DataFrame() # Empty fallback

def download_segments(client_id):
    user = CustomUser.objects.get(id=client_id)
    audio_segments = AudioSegment.objects.filter(
        owner=user,
        segment_file_remote__isnull=False
    )
    # Map from original filename to local path after downloading from S3
    segment_lookup = {}
    if not audio_segments.exists():  # Check if queryset is empty
        logger.info(f"No remote segments found for user {client_id}")
        return segment_lookup

    for segment in audio_segments:
        file_name = os.path.basename(segment.segment_file_remote.name)
        # Download from S3 and store in local_storage
        try:
            with segment.segment_file_remote.open("rb") as remote_file:
                # Save the remote file locally
                segment.segment_file_local.save(
                    file_name,
                    remote_file,
                    save=True
                )
                # Store local path to map
                local_path = segment.segment_file_local.path  # absolute path in local_storage
                segment_lookup[file_name] = local_path
        except Exception as e:
            logger.info(f"Failed to download {file_name}: {e}")
            continue  # Skip failed downloads
    return segment_lookup

@shared_task(bind=True, routing_key="downloading_processing")
def download_user_files_from_remote(self, client_id):
    try:
        # Set up storing path with clean up
        output_dir = os.path.join(BASE_DIR, 'local_media', 'uploads', str(client_id))
        os.makedirs(os.path.dirname(output_dir), exist_ok=True)
        output_path = os.path.join(output_dir, 'combined_audio_metadata.csv')
        # Clean up previous file at output_path if exists
        if os.path.exists(output_path):
            os.remove(output_path)

        # Get combined Metadata
        combined_csv = get_user_metadata(client_id)
        if combined_csv.empty:
            logger.warning(f"No metadata found for client {client_id}")
            return {"status": "skipped", "reason": "empty_metadata"}

        # Download segment files
        segment_lookup = download_segments(client_id)
        # Update audio paths
        if "audio_path" in combined_csv.columns:
            def map_path(row):
                audio_path = row.get("audio_path")
                # Not all audio_path is a valid string, Pandas represents missing value as NaN and are type of float
                if not isinstance(audio_path, str) or pd.isna(audio_path):
                    return audio_path
                file_name = os.path.basename(audio_path)
                return segment_lookup.get(file_name, audio_path)

            combined_csv["audio_path"] = combined_csv.apply(map_path, axis=1)
        # Save
        combined_csv.to_csv(output_path, index=False, encoding='utf-8-sig')
    except Exception as e:
        return {"status": "error", "error": str(e)}

@shared_task(bind=True, routing_key="video_processing")
def process_audio_file(self, media_file_id):
    audio_file = MediaFile.objects.get(id=media_file_id)
    audio_file.processing_status = 'processing'
    audio_file.save()
    try:
        process_audio(audio_file)
        audio_file.refresh_from_db()
        audio_file.processing_status = 'completed'
        audio_file.save()
    except Exception as e:
        audio_file.processing_status = 'failed'
        audio_file.metadata['error'] = str(e)
        audio_file.save()
        raise

@shared_task(bind=True, routing_key="video_processing")
def process_audio_clips(self, media_file_id):
    media_file = MediaFile.objects.get(id=media_file_id)
    media_file.processing_status = 'processing'
    media_file.save()
    try:
        create_audio_clips(media_file.id)
        """
        media_file.metadata_file gets updated in create_audio_clips, so do a hard
        refresh to ensure the updated metadata_file reference is included when
        saving the processing_status.
        """
        media_file.refresh_from_db()
        media_file.processing_status = 'completed'
        media_file.save()
    except Exception as e:
        self.retry(exc=e, countdown=10, max_retries=3)  # Retry logic if failure
        media_file.processing_status = 'failed'
        media_file.metadata['error'] = str(e)
        media_file.save()
        raise

@shared_task(bind=True, routing_key="caption_processing")
def process_subtitle_file(self, media_file_id):
    """Process subtitle file - convert to CSV and clean"""
    subtitle_file = MediaFile.objects.get(id=media_file_id)
    subtitle_file.processing_status = 'processing'
    subtitle_file.save()

    try:
        convert_subtitles_to_metadata(media_file_id)
        subtitle_file.refresh_from_db()
        subtitle_file.processing_status = 'completed'
        subtitle_file.save()
    except Exception as e:
        subtitle_file.processing_status = 'failed'
        subtitle_file.metadata['error'] = str(e)
        subtitle_file.save()
        raise

# Don't need to store task result, especially when payload is too large
@shared_task(bind=True, routing_key="default", base=SuccessEmailTask)
def compile_training_dataset(self, channel_id, media_file_id):
    """Compile and upload training dataset"""
    media_file = MediaFile.objects.get(id=media_file_id)
    file = media_file._metadata_file
    output_path = os.path.join('uploads', str(channel_id), 'combined_audio_metadata.csv')
    channel_exist = os.path.exists(output_path)
    try:
        new_csv_file = pd.read_csv(
            media_file.metadata_file,
            encoding="utf-8-sig",
            on_bad_lines="skip",
            sep=","
        )

        if channel_exist: # Concatenate new dataset to old
            existing_csv = pd.read_csv(
                output_path,
                encoding="utf-8-sig",
                on_bad_lines="skip",
                sep=","
            )
            combined_csv = pd.concat([existing_csv, new_csv_file], ignore_index=True)
        else:
            combined_csv = new_csv_file
        # Remove duplicate rows and save
        combined_csv = combined_csv.drop_duplicates()
        # Save combined_csv back to same path
        combined_csv.to_csv(output_path, index=False, encoding="utf-8-sig")
        return True
    except Exception as e:
        logger.info(f"Failed to compile dataset: {e}")
        raise

# @shared_task(bind=True, routing_key="default")
# def push_to_hf(self, channel_id):
#     output_path = os.path.join(BASE_DIR, 'local_media', 'uploads', str(channel_id), 'combined_audio_metadata.csv')
#     dataset = pd.read_csv(
#                 output_path,
#                 encoding="utf-8-sig",
#                 on_bad_lines="skip",
#                 sep=","
#             )
#     upload_to_huggingface(dataset, channel_id)

# @shared_task(bind=True, routing_key="default")
# def clear_segment_files(self, channel_id):
#     logger.info(f"Channel id: {channel_id}")
#     user = CustomUser.objects.get(id=channel_id)
#     audio_segments = AudioSegment.objects.filter(owner=user, segment_file_remote__isnull=False)
#     # First store segment file local names into a list
#     segment_file_names = [file.segment_file_local.name for file in audio_segments]
#     # Delete local segment files
#     if segment_file_names:
#         for file_name in segment_file_names:
#             local_storage.delete(file_name)
#     for segment in audio_segments:
#         segment.segment_file_local = None
#         segment.save(update_fields=['segment_file_local'])
#     # delete the .csv file
#     root = settings.LOCAL_MEDIA_ROOT
#     file_path = Path(root) / str(channel_id) / "mediafile"
#     logger.info(f"Media File Path: {file_path}")
#     # file_path = os.path.join(BASE_DIR, 'local_media', 'uploads', str(channel_id), 'combined_audio_metadata.csv')
#     if os.path.exists(file_path):
#         os.remove(file_path)
#         logger.info(f"Removed combined CSV: {file_path}")



@shared_task(bind=True, routing_key="default")
def clear_segment_files(self, channel_id):
    logger.info("Channel id: %s", channel_id)

    user = CustomUser.objects.get(id=channel_id)
    audio_segments = AudioSegment.objects.filter(
        owner=user, segment_file_remote__isnull=False
    )

    # ------------------------------------------------------------------ #
    # Delete local clip files – skip blanks                              #
    # ------------------------------------------------------------------ #
    for seg in audio_segments:
        if seg.segment_file_local and seg.segment_file_local.name:
            try:
                local_storage.delete(seg.segment_file_local.name)
            except FileNotFoundError:
                pass                         # already gone – ignore
        seg.segment_file_local = None
        seg.save(update_fields=["segment_file_local"])

    # ------------------------------------------------------------------ #
    # Remove legacy combined CSV (if you still keep one)                 #
    # ------------------------------------------------------------------ #
    file_path = (
        Path(settings.LOCAL_MEDIA_ROOT) / str(channel_id) / "mediafile"
    )
    logger.info("Media File Path: %s", file_path)

    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info("Removed combined CSV: %s", file_path)

@shared_task(bind=True, routing_key="default", base=SuccessEmailTask)
def push_to_hf(self, media_file_id):
    media_file = MediaFile.objects.get(id=media_file_id)
    channel = CustomUser.objects.get(id=media_file.owner.id)
    channel_id  = media_file.owner_id   
    # dataset = compile_dataset(media_file.metadata_file)
    # csv_path = compile_dataset(channel_id)
    # dataset= pd.read_csv(csv_path, encoding="utf-8-sig")
    # dataset = compile_training_dataset(channel_id, media_file_id)
    upload_to_huggingface(media_file_id)
    clear_segment_files(channel_id)
    logger.info(f"Pushed to Huggingface and cleared segment files for {media_file_id}")
    


# @shared_task(bind=True, routing_key="default")
# def clear_segment_files(self, media_file_id):
#     media_file = MediaFile.objects.get(id=media_file_id)
#     for segment_file in media_file.audio_segments.all():
#         segment_file.delete()

# # This is a test function used in the temporary admin dashboard page
# # to trigger the processing pipeline for a specific audio file. In the future
# # the processing steps will happen separately from the compile_training_dataset step.
# def process_and_upload(original_file_id, subtitle_file_id):
#     # original_file = MediaFile.objects.get(id=original_file_id)
#     # Check if the original media file exists.
#     try:
#         original_file = MediaFile.objects.get(id=original_file_id)
#     except MediaFile.DoesNotExist:
#         # Optionally, log this error and/or return an error message.
#         raise ValueError(f"MediaFile with id {original_file_id} does not exist.")

#     # Verify that the original file actually has a file associated.
#     if not original_file.file:
#         raise ValueError("The original video file has no file associated with it.")

#     # Check that a caption file ID is provided.
#     if not subtitle_file_id:
#         raise ValueError("No caption file was selected.")

#     # Check that the caption file exists.
#     try:
#         subtitle_file = MediaFile.objects.get(id=subtitle_file_id)
#     except MediaFile.DoesNotExist:
#         raise ValueError(f"Subtitle file with id {subtitle_file_id} does not exist.")

#     # Verify that the caption file actually has a file.
#     if not subtitle_file.file:
#         raise ValueError("The caption file has no file associated with it.")

#     # Optional: Check that the caption file seems to correspond to the video.
#     # For example, you could compare the base filenames:
#     video_basename = os.path.splitext(original_file.original_filename)[0]
#     caption_basename = os.path.splitext(subtitle_file.original_filename)[0]
#     if video_basename not in caption_basename:
#         raise ValueError("The caption file does not appear to correspond to the video file.")

#     _, ext = os.path.splitext(original_file.file.name)
#     is_video = ext.lower() == '.mp4'
#     if is_video:
#         process_video_file.delay(original_file_id)

#     process_audio_file.delay(original_file_id)
#     process_subtitle_file.delay(subtitle_file_id)
#     process_audio_clips.delay(original_file_id)
#     push_to_hf.delay(original_file_id)
