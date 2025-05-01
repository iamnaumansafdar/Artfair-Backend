from rest_framework import serializers
from rest_framework import serializers
from .models import VideoFile, MediaFile

class MediaFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile
        fields = ['id', 'owner', 'file', 'file_path', 'file_type', 'file_size', 'md5_hash', 'processing_status', 'metadata']
        read_only_fields = ['file_path', 'file_type', 'file_size', 'md5_hash', 'processing_status', 'metadata']
        

class VideoFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoFile
        fields = ['file', 'ass_file'] 

    def to_representation(self, instance):
        # Get the MediaFile instance associated with the VideoFile
        media_file = MediaFile.objects.get(pk=instance.pk) 
        
        # Create a dictionary with the file and ass_file fields from MediaFile
        data = {
            'file': media_file.file.url if media_file.file else None, 
            'ass_file': media_file.ass_file.url if media_file.ass_file else None,
        }
        return data
