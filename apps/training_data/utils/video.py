import os
import subprocess
from io import BytesIO
from ..models import MediaFile
from .audio import WHISPER_SAMPLE_RATE
from pydub import AudioSegment as PydubAudioSegment  # Renamed to avoid conflict
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def convert_video_to_audio(media_file_id):
    """Convert video to audio using pydub"""
    
    try:
        video_file = MediaFile.objects.get(id=media_file_id)
        # Download video file to temp storage
        video_file.file.seek(0)
        video_data = video_file.file.read()
        video_temp = BytesIO(video_data)

        # Convert to audio using pydub
        video = PydubAudioSegment.from_file(video_temp)  # Using renamed import
        audio = video.set_frame_rate(WHISPER_SAMPLE_RATE)  # Set to 16kHz for Whisper compatibility

        # Save to temp buffer
        audio_buffer = BytesIO()
        audio.export(audio_buffer, format='wav')
        audio_buffer.seek(0)  # Reset buffer position to start

        # Save to MediaFile
        video_file.processed_audio_file.save(
            f"{video_file.file_name}.wav",
            audio_buffer,
            save=True
        )

    except Exception as e:
        raise Exception(f"Error converting video to audio: {str(e)}")




def get_video_duration_seconds(file_path):
    """
    Use ffprobe to get the video's duration in seconds.
    Note: Requires that ffprobe is installed on your system.
    """
    try:
        command = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        return float(output.strip())
    except Exception as e:
        print(f"Error retrieving video duration for {file_path}: {e}")
        return 0.0

def format_duration(seconds):
    """
    Format the duration.
      - If less than 1 hour, return minutes (e.g. "45.0 minutes").
      - If 1 hour or more, return an "HH:MM:SS" string.
    """
    if seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}:{minutes:02}:{secs:02}"
