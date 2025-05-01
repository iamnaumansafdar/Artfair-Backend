import os
from rest_framework import serializers
from apps.training_data.models import MediaFile, AudioSegment, Speaker
from django.template.defaultfilters import filesizeformat
from django.contrib.auth import get_user_model
User = get_user_model()


class FileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(write_only=True)
    original_filename = serializers.CharField(
        max_length=255, 
        required=True
    )

    class Meta:
        model = MediaFile
        fields = ["user_email", "original_filename"]


class FileSerializerForOrphanFiles(FileSerializer):
    file_name = serializers.SerializerMethodField()
    is_caption = serializers.SerializerMethodField()

    class Meta:
        model = MediaFile
        fields = ["id", "file_name", "is_caption"]
        
    def get_is_caption(self, obj):
        return obj.file_type == "ass"

    def get_file_name(self, obj):
        file_name = obj.original_filename
        split_name = file_name.split(".")
        return "_".join(split_name[0].split("_")[2:])


class FileSerializerForCreate(FileSerializer):
    processing_status = serializers.CharField(
        max_length=50,
        default='pending'
    )
    file_size = serializers.SerializerMethodField()
    linked_video_matched = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = MediaFile
        fields = ["id", "original_filename", "processing_status", "linked_video_matched", "file_size", "created_at"]
    
    def get_linked_video_matched(self, obj):
        return obj.linked_file is not None 

    def get_file_size(self, obj):
        return filesizeformat(obj.file_size)
    
    def get_created_at(self, obj):
        formatted_date = obj.created_at.strftime("%Y-%m-%d")
        formatted_time = obj.created_at.strftime("%H:%M")
        return f"{formatted_date} {formatted_time}" 
    
    
class AudioSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioSegment
        fields = ['id', 'segment_file_remote']


class CaptionFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile
        # We include the fields that are relevant.
        fields = ['id', 'original_filename', 'file_type', 'S3URL']


class UserNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name")


class LinkedMediaFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile
        fields = ("id", "original_filename", "S3URL", "file_type")

class MediaFileSerializer(serializers.ModelSerializer):
    owner = UserNestedSerializer(read_only=True)
    linked_file = LinkedMediaFileSerializer(read_only=True)
    processing_status = serializers.CharField(max_length=50, default='pending')
    file_size = serializers.SerializerMethodField()
    linked_video_matched = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = MediaFile
        fields = [
            "id", "owner", "linked_video_matched", "original_filename", "file_type",  "linked_file",
            "S3URL", "file_size", "md5_hash", "processing_status", "metadata", "is_source_file", "description",
            "license_content_agreed", "created_at", "updated_at"
        ]

    def get_linked_video_matched(self, obj):
        return obj.linked_file is not None

    def get_file_size(self, obj):
        # Use your safe file size property (see earlier advice)
        return filesizeformat(obj.file_size)

    def get_created_at(self, obj):
        formatted_date = obj.created_at.strftime("%Y-%m-%d")
        formatted_time = obj.created_at.strftime("%H:%M")
        return f"{formatted_date} {formatted_time}"

    def get_updated_at(self, obj):
        formatted_date = obj.created_at.strftime("%Y-%m-%d")
        formatted_time = obj.created_at.strftime("%H:%M")
        return f"{formatted_date} {formatted_time}"


class MediaFileUpdateSerializer(serializers.ModelSerializer):
    # Optionally add these if you want them formatted in the response.
    # linked_file = LinkedMediaFileSerializer(read_only=True)
    linked_file = serializers.PrimaryKeyRelatedField(
        queryset=MediaFile.objects.all()
    )


    linked_video_matched = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = MediaFile
        fields = [
            "id",
            "original_filename",
            "file_type",
            "linked_video_matched",
            "linked_file",
            "S3URL",
            "file_size",
            "md5_hash",
            "processing_status",
            "description",
            "license_content_agreed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("owner", "created_at", "updated_at", "md5_hash")

    def get_file_size(self, obj):
        # Make sure file_size is either calculated from your model or use safe_file_size
        return filesizeformat(obj.file_size)

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d %H:%M")

    def get_linked_video_matched(self, obj):
        return obj.linked_file is not None
    
    
    def validate(self, data):
        if 'linked_file' in data or (self.instance and self.instance.linked_file):
            linked_file = data.get("linked_file") or self.instance.linked_file
            if not linked_file:
                raise serializers.ValidationError({
                    "linked_file": "The caption file has no file associated with it."
                })
            video_basename = os.path.splitext(self.instance.original_filename)[0] if self.instance.original_filename else ""
            caption_basename = os.path.splitext(linked_file.original_filename or "")[0]
            if video_basename and (video_basename not in caption_basename):
                raise serializers.ValidationError({
                    "linked_file": "The caption file does not appear to correspond to the video file."
                })
        return data


class SpeakerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=255, 
        required=True
    )

    class Meta:
        model = Speaker
        fields = ["id", "name"]



class TotalVideoHoursSerializer(serializers.Serializer):
    video_count = serializers.IntegerField()
    total_hours = serializers.CharField(
        help_text="Either a decimal number of hours (e.g. '2.50') or an HH:MM:SS string, depending on call."
    )


class DownloadUrlSerializer(serializers.Serializer):
    url = serializers.URLField()