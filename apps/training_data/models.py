# training_data/models.py
import os
from django.db import models
from django.core.files.storage import default_storage, FileSystemStorage
from django.conf import settings
from conf.settings import BASE_DIR
from apps.users.models import TimestampMixin


# ------------------------------------------------------------------ #
#  Rights-owner entity (YouTube channel, podcast, label…)
# ------------------------------------------------------------------ #
class Channel(TimestampMixin):       
    title = models.CharField(max_length=200)          #brand Name “NPR”
    
    def __str__(self):
        return f"{self.title}"
    
class ChannelMember(models.Model):
    class Role(models.TextChoices):
        OWNER  = "owner",  "Owner"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    channel = models.ForeignKey(Channel, on_delete=models.CASCADE,related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="channel_roles")
    role = models.CharField(max_length=10, choices=Role.choices,  default=Role.OWNER)   
    
    
    def __str__(self):
        return f"{self.user.email} - {self.role}"


def get_upload_path(instance, filename):
    """Generate upload path based on client and file type"""
    base_filename = os.path.basename(filename)
    return f"uploads/{instance.owner.id}/{instance._meta.model_name}/{base_filename}" if instance and instance.owner else  f"uploads/{instance._meta.model_name}/{base_filename}"

class MediaFile(TimestampMixin, models.Model):
    """Base model for all uploaded media files"""
    FILE_TYPES = [
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('ass', 'Caption')
    ]
    SPLITS = [
        ('train', 'train'),
        ('test', 'test'),
        ('val', 'val')
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='media_files')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='channel_media_files', null=True, blank=True)
    '''
    The user-uploaded file. This will either be a source video/audio file, or a caption
    file which belongs to a source file. They are linked via the source_file foreign key.
    '''
    file = models.FileField(upload_to=get_upload_path, blank=True, null=True)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    file_type = models.CharField(max_length=50, choices=FILE_TYPES, blank=True, null=True)

    '''Represents the relationship between a caption file and its source audio or video file'''
    linked_file = models.OneToOneField(
        'training_data.MediaFile',
        on_delete=models.SET_NULL,
        related_name='_caption_file',
        verbose_name="Link Source File Here",
        null=True,
        blank=True
    )
    '''
    The csv metadata file is created during the processing pipeline, and should only
    be stored on a source file, *not* on a caption file.
    A metadata_file getter/setter are defined below to ensure it's accessed from and stored
    consistently on the source file.
    '''
    _metadata_file = models.FileField(upload_to=get_upload_path, blank=True, null=True)

    ''' The audio file that gets extracted during the processing pipeline and used for audio segmentation.'''
    processed_audio_file = models.FileField(upload_to=get_upload_path, blank=True, null=True)
    split = models.CharField(max_length=50, choices=SPLITS, blank=True, null=True)
    S3URL = models.CharField(max_length=255, default="", blank=True, null=True)
    file_size = models.BigIntegerField(editable=False, null=True)
    md5_hash = models.CharField(max_length=32, editable=False, null=True)
    processing_status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    metadata = models.JSONField(default=dict, blank=True, null=True)
    is_source_file = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    license_content_agreed = models.BooleanField(default=False)
    video_duration = models.CharField(max_length=50,null=True,blank=True, help_text="Length of the video in HH:MM:SS format")

    def __str__(self):
        return f"{self.owner.email} - {self.original_filename}"
    
    def delete(self, *args, **kwargs):
        # Delete the actual file when the model is deleted
        if self.file:
            default_storage.delete(self.file.name)
        super().delete(*args, **kwargs)

    def _get_linked_file(self):
        '''
        Returns the associated MediaFile, or None if there isn't one.

        Ideally, we'd enforce a one-way link, where the linked_file FK always gets set on a caption file and
        points to its source audio/video file. Until then, since files can be linked in any direction, we
        this helper checks both forward/backward associations to check for an associated MediaFile.
        '''
        return self.linked_file or (self._caption_file if hasattr(self, '_caption_file') else None)

    @property
    def _source_file(self):
        '''
        Returns the source file associated with this file if there is one, otherwise returns None.
        If this file is a source file, return itself.

        A source file is a video or audio file uploaded by a user, which caption files are associated to.
        '''
        if self.file_type in ['video', 'audio']:
          return self
        linked_file = self._get_linked_file()
        if linked_file and linked_file.file_type in ['video', 'audio']:
            return linked_file

    @property
    def caption_file(self):
        '''
        Returns the caption file associated with this file, or None if there isn't one.
        '''
        linked_file = self._get_linked_file()
        if linked_file and linked_file.file_type == 'ass':
            return linked_file

    @property
    def full_file_name(self):
        '''Return the filename with extension.'''
        return os.path.basename(self.file.name)

    @property
    def file_name(self):
        '''Return the filename without extension.'''
        return os.path.splitext(os.path.basename(self.file.name))[0]

    @property
    def source_file_name(self):
        '''
        Return the file name (without extension) of the source file.

        If this is a caption file, returns the associated source file. If this is
        a source file already (if it's a video or audio file), return this file's name.
        '''
        return self._source_file.file_name

    @property
    def metadata_file(self):
        '''
        Gets the metadata file associated with this file. If this file has a source file,
        it will be stored there.
        '''
        return self._source_file._metadata_file

    @metadata_file.setter
    def metadata_file(self, value):
        '''
        Saves the metadata file to the source file. Note that instead of directly saving the
        metadata file to an instance, like instance._metadata_file.save(...), we should set it
        using this property to ensure the relations are set up properly. For an example,
        see #convert_subtitles_to_metadata in utils/metadata.py.
        '''

        source_file = self._source_file
        source_file._metadata_file = value
        source_file.save(update_fields=['_metadata_file'])
        
    @property
    def safe_file_size(self):
        if self.file:
            exists = default_storage.exists(self.file.name)
            print(f"Checking file {self.file.name}: exists={exists}")
            if exists:
                try:
                    return self.file.size
                except Exception as e:
                    print(f"Error getting file size for {self.file.name}: {e}")
                    return 0
        return 0   

local_storage = FileSystemStorage(location=os.path.join(BASE_DIR, 'local_media'))

class AudioSegment(MediaFile):
    """Processed audio segments from video or audio files"""
    source_audio = models.ForeignKey(MediaFile, on_delete=models.CASCADE, related_name='audio_segments')
    # This FileField stores segment files locally since Hugging Face requires a local file path for access.
    segment_file_local = models.FileField(upload_to=get_upload_path, storage=local_storage, blank=True, null=True)
    segment_file_remote = models.FileField(upload_to=get_upload_path, blank=True, null=True)

    def clean(self):
        super().clean()
        if self.file and not self.file_type in ['mp3', 'wav', 'aac']:
            from django.core.exceptions import ValidationError
            raise ValidationError('Invalid audio file format')



# ----------------------------------
# Speaker Model
# ----------------------------------
class Speaker(TimestampMixin, models.Model):
    """
    Represents a unique speaker whose voice appears in one or more videos.
    Speaker data is extracted from caption files. Each speaker is uniquely identified by a
    speaker_id generated from the speaker's name and channel (rights owner) id.
    """
    speaker_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    primary_language = models.CharField(max_length=100, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=50, blank=True, null=True)
    
    # Link each speaker to the rights owner (channel). You can extend this to a separate Channel model if needed.
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='speakers')
    media_files = models.ManyToManyField(
        'MediaFile',
        related_name='speakers',
        blank=True
    )

    extra_metadata = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ("name", "-created_at",)
    
    def __str__(self):
        return f"speaker name: {self.name}, speaker id: ({self.speaker_id})"