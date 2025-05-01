from django.shortcuts import render
# Create your views here.
from rest_framework import generics
from .serializers import VideoFileSerializer
from .models import VideoFile
from .tasks import extract_metadata, convert_video_to_audio

class VideoFileUploadView(generics.CreateAPIView):
    serializer_class = VideoFileSerializer

    def perform_create(self, serializer):
        video = serializer.save(owner=self.request.user)
        extract_metadata.delay(video.id)  # Call extract_metadata asynchronously
        convert_video_to_audio.delay(video.id)  # Call convert_video_to_audio asynchronously
        return video