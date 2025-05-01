import json

import boto3
from botocore.exceptions import NoCredentialsError
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiResponse
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from apps.training_data.models import Speaker
from apps.training_data.tasks import *
from .serializers import CaptionFileSerializer, SpeakerSerializer
from .serializers import FileSerializerForCreate, FileSerializerForOrphanFiles
from .serializers import MediaFileSerializer, MediaFileUpdateSerializer
from apps.training_data.models import get_upload_path
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from celery import chain, chord
from django.core.exceptions import ValidationError
from apps.training_data.models import ChannelMember, Channel
from knox.auth import TokenAuthentication as KnoxTokenAuthentication
from apps.training_data.utils.video import format_duration
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
import traceback
from .schema import (
    CAPTION_FILE_LIST_RESPONSE_SCHEMA,
    SPEAKER_LIST_RESPONSE_SCHEMA,
    MEDIAFILE_LIST_RESPONSE_SCHEMA,
    TOTAL_VIDEO_HOURS_RESPONSE_SCHEMA,
    TOTAL_VIDEO_HOURS_RESPONSE_SCHEMA,
    DOWNLOAD_MEDIAFILE_RESPONSE_SCHEMA,
)

def get_user_primary_channel(user) -> Channel:
    try:
        return (
            ChannelMember.objects
            .filter(user=user, role=ChannelMember.Role.OWNER)
            .select_related("channel")
            .first()
            .channel    # might raise AttributeError if .first() returns None
        )
    except AttributeError:
        raise ValidationError("Uploader does not own a channel")


@api_view(['POST'])
def create_file_upload(request):
    serializer = FileSerializerForCreate(data=request.data, many=True)
    try:
        # Handling multiple entries in one request using bulk_create
        media_files = []
        fileSpeakerMap = {}
        print("request data", request.data)
        if serializer.is_valid():
            prev_user = None
            for file_meta in request.data:
                user_email = file_meta["user_email"]
                try:
                    user = prev_user
                    # Only query CustomUser table when current file_meta user is different from the previous user.
                    if user == None or user_email != user.email:
                        user = CustomUser.objects.get(email=user_email)
                        # find (or reuse) the uploader’s primary channel
                        channel = get_user_primary_channel(user)
                    if "linked_file_id" in file_meta:
                        linked_file = MediaFile.objects.get(id=file_meta["linked_file_id"])
                    else:
                        linked_file = None
                    # If user has selected speaker for the file, add it to the fileSpeakerMap
                    if file_meta.get("speaker_list"):
                        fileSpeakerMap[file_meta["original_filename"]] = file_meta["speaker_list"]
                    file_meta_data = MediaFile(
                        owner=user,
                        channel= channel,   
                        original_filename=file_meta["original_filename"],
                        S3URL=file_meta["s3_url"],
                        file_type=file_meta["fileType"],
                        file_size=file_meta["fileSize"],
                        is_source_file=file_meta["isSourceFile"],
                        linked_file=linked_file,
                        description=file_meta.get("description", ""),
                        license_content_agreed=file_meta.get("license_content_agreed", False),
                        md5_hash=file_meta["md5Hash"],
                    )
                    media_files.append(file_meta_data)
                    prev_user = user
                except CustomUser.DoesNotExist:
                    raise NotFound(detail="User with the provided email does not exist.", code=status.HTTP_400_BAD_REQUEST)

            for media_instance in media_files:
                file_key = media_instance.S3URL.replace(
                    f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/", ""
                )
                media_instance.file.name = file_key.replace("+", " ")

            new_file_metadata = MediaFile.objects.bulk_create(media_files)
            for metadata in new_file_metadata:
                file_name = metadata.original_filename
                if file_name in fileSpeakerMap:
                    metadata.speakers.set(fileSpeakerMap[file_name])
            serialized = FileSerializerForCreate(new_file_metadata, many=True)
            return Response(serialized.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        logger.error("create_file_upload crashed\n%s", traceback.format_exc())
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET']) 
def get_orphan_files(request, user_email):
    """
    Get all orphan media files for a user
    """
    user = CustomUser.objects.get(email=user_email)
    files = MediaFile.objects.filter(
        owner=user,
        linked_file=None,
        processing_status="pending",
    )

    serializer = FileSerializerForOrphanFiles(
        files, 
        context={"request": request},
        many=True
    )

    return Response({"orphan_files": serializer.data}, status=status.HTTP_200_OK)

if settings.REMOTE_STATIC_FILES:
    s3_client = boto3.client(
        's3',
        region_name=settings.AWS_S3_REGION,
    )
else:
    s3_client = None


@csrf_exempt
def generate_s3_presigned_url(request):
    data = json.loads(request.body)
    file_name = data.get('file_name')
    file_type = data.get('file_type')

    try:
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': file_name,
                'ContentType': file_type
            },
            ExpiresIn=3600
        )
        return JsonResponse(
            {
                'url': presigned_url,
                'fields': {
                    'key': file_name,
                    'content-type': file_type
                },
                "method": "PUT",
                "headers": {
                    'content-type': file_type
                }
            }
        )
    except (NoCredentialsError, Exception) as e:
        return JsonResponse({'error': str(e)}, status=403)


@csrf_exempt
@api_view(['POST'])
def create_s3_multipart(request):
    data = request.data
    file_type = data["type"]
    file_name = data["file_name"]
    try:
        res = s3_client.create_multipart_upload(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=file_name,
            ContentType=file_type
        )
        return JsonResponse({
            "uploadId": res["UploadId"],
            "key": res["Key"]
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
def s3_multipart_listParts(request, uploadId):
    data = request.data
    try:
        res = s3_client.list_parts(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            UploadId=uploadId,
            Key=data["key"]
        )
        return JsonResponse({
            "parts": res["Parts"]
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
def s3_multipart_signPart(request, uploadId, partNumber):
    data = request.data
    try:
        url = s3_client.generate_presigned_url(
            "upload_part",
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': data["key"],
                "UploadId": uploadId,
                "PartNumber": partNumber
            },
            ExpiresIn=3600
        )
        return JsonResponse({
            "url": url
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@api_view(['DELETE'])
def s3_multipart_abort(request, uploadId):
    data = request.data
    try:
        s3_client.abort_multipart_upload(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=data["key"],
            UploadId=uploadId
        )
        return JsonResponse({})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
def s3_multipart_complete(request, uploadId):
    data = request.data
    parts = data.get("parts")
    file_key = data.get("key")

    try:
        res = s3_client.complete_multipart_upload(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=file_key,
            UploadId=uploadId,
            MultipartUpload={"Parts": parts}
        )

        return JsonResponse({
            'message': 'Multipart upload completed successfully',
            'name': res.get('Key'),
            "S3URL": res.get("Location")
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@extend_schema(
    responses=CAPTION_FILE_LIST_RESPONSE_SCHEMA,
    summary="List Caption Files",
    description="Retrieve a list of all caption files for the authenticated user. Each caption file includes its S3 URL and metadata."
)
class ListUserCaptionFilesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        # Query for caption files (file_type 'ass') owned by the current user.
        caption_files = MediaFile.objects.filter(owner=request.user, file_type='ass')
        serializer = CaptionFileSerializer(caption_files, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)





@extend_schema(
    responses=SPEAKER_LIST_RESPONSE_SCHEMA,
    description="Retrieve a list of speakers associated with the authenticated user."
)
class SpeakerViewSet(viewsets.ModelViewSet):
    """
    CRUD API endpoint for Speakers.
    - GET /speakers/ returns speakers for the logged in user.
    - POST /speakers/ creates new speaker(s). Provide a JSON object for single creation or a JSON array for bulk creation.
    - PUT/PATCH /speakers/{id}/ updates a speaker.
    - DELETE /speakers/{id}/ deletes a speaker.
    """
    serializer_class = SpeakerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return speakers for the logged-in user.
        return Speaker.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # Automatically assign the rights owner based on the logged-in user.
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        # Support bulk creation if a list is provided.
        request_names = request.data.get("names")
        speaker_data = [Speaker(
            owner = self.request.user,
            name = name
        ) for name in request_names]
        new_speakers = Speaker.objects.bulk_create(speaker_data)
        serialized = self.get_serializer(new_speakers, many=True)
        headers = self.get_success_headers(serialized.data)
        return Response(serialized.data, status=status.HTTP_201_CREATED, headers=headers)


@extend_schema(
    responses=MEDIAFILE_LIST_RESPONSE_SCHEMA,
    description=(
        "Retrieve all media files for the authenticated user. "
        "Optional query parameter 'file_type' filters results by 'video', 'audio' or 'ass'."
    )
)
@api_view(['GET'])
def list_media_files(request):
    """
    List all media files for the authenticated user.
    Optional query param: file_type=(video|audio|ass)
    Example calls:
      - GET /api/mediafiles/?file_type=video
      - GET /api/mediafiles/?file_type=ass
      - GET /api/mediafiles/ (no filter => all user's files)
    """
    if not request.user.is_authenticated:
        return Response({"detail": "Not authenticated"}, status=401)

    file_type = request.query_params.get('file_type')
    qs = MediaFile.objects.filter(owner=request.user)

    if file_type in ['video', 'audio', 'ass']:
        qs = qs.filter(file_type=file_type)

    # Optionally, other filters like show only unmatched (linked_file=None)
    # e.g. `unmatched = request.query_params.get('unmatched', 'false')`

    serializer = MediaFileSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data, status=200)



@extend_schema(
    responses={200: OpenApiResponse(
        response=MediaFileUpdateSerializer,
        description="MediaFile updated successfully."
    )},
    summary="Update Media File",
    description=(
        "Update fields of a media file (e.g. linked_file, description, license_content_agreed, speaker information). "
        "This endpoint supports partial updates."
    )
)

class MediaFilePartialUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/mediafiles/{id}/
    Fields that can be updated include:
      - linked_file
      - description
      - license_content_agreed
      - possibly speaker_id or speaker_ids
    """
    queryset = MediaFile.objects.all()
    serializer_class = MediaFileUpdateSerializer
    authentication_classes = [KnoxTokenAuthentication]
    permission_classes     = [IsAuthenticated]
    lookup_url_kwarg = 'pk'

    def get_queryset(self):
        # Only allow updates to the user's own files
        return MediaFile.objects.filter(owner=self.request.user)



    def perform_update(self, serializer):
        instance = serializer.save()

        # Identify source vs caption
        if instance and instance.file_type and instance.file_type in ('video','audio'):
            source = instance
            caption = instance.linked_file
        elif instance and instance.file_type and instance.linked_file and instance.file_type == 'ass':
            caption = instance
            source = instance.linked_file
        else:
            source = caption = None

        # Build one long chain:
        tasks = []

        # 1) Source pipeline
        if source:
            if source.file_type == 'video':
                tasks += [
                    process_video_file.si(source.id),
                    process_audio_file.si(source.id),
                ]
            elif source.file_type == 'audio':
                tasks.append(process_audio_file.si(source.id))

        # 2) Caption pipeline (runs only after source tasks complete)
        if caption and caption.file_type == 'ass':
            tasks += [
                process_subtitle_file.si(caption.id),
                process_audio_clips.si(source.id),
            ]

        # 3) Push to HF (runs after everything else)
        final_id = source.id if source else caption.id
        tasks.append(push_to_hf.si(final_id))

        # Fire the entire chain
        if tasks:
            chain(*tasks).apply_async()
        else:
            push_to_hf.delay(instance.id)





@extend_schema(
    parameters=[
        OpenApiParameter(
            "video_id",
            OpenApiTypes.INT,
            OpenApiParameter.QUERY,
            required=False,
            description="If provided, returns just that video’s duration."
        )
    ],
    responses=TOTAL_VIDEO_HOURS_RESPONSE_SCHEMA,
    description="Get total hours for all videos, or a single video if `video_id` is passed."
)
class TotalVideoHoursView(APIView):
    """
    GET /api/v1/training_data/total-video-hours/?video_id=<id>

    If `video_id` is provided:
      - 404 if not found or not owned by this user
      - 400 if that file isn’t a video
      - otherwise: return the duration of just that video

    If no `video_id`:
      - sum across *all* this user’s videos
    """
    authentication_classes = [KnoxTokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request, format=None):
        video_id = request.query_params.get("video_id")

        if video_id:
            # fetch exactly one file (or 404)
            media = get_object_or_404(
                MediaFile.objects.filter(owner=request.user),
                pk=video_id
            )

            # if it isn't a video, reject
            if media.file_type != "video":
                return Response(
                    {"detail": "Only video files have a duration."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                seconds = int(media.video_duration)
            except (TypeError, ValueError):
                # fallback if you ever store as "HH:MM:SS"
                h, m, s = map(int, media.video_duration.split(":"))
                seconds = h*3600 + m*60 + s

            return Response({
                "video_count": 1,
                "total_hours": format_duration(seconds)
            })

        # no specific video → sum *all* videos
        videos = MediaFile.objects.filter(
            owner=request.user,
            file_type="video"
        ).exclude(video_duration__in=[None, ""])

        total_seconds = 0
        for v in videos:
            try:
                total_seconds += int(v.video_duration)
            except (TypeError, ValueError):
                # in case you ever store "HH:MM:SS"
                parts = v.video_duration.split(":")
                if len(parts) == 3:
                    h, m, s = map(int, parts)
                    total_seconds += h*3600 + m*60 + s

        return Response({
            "video_count": videos.count(),
            "total_hours": format_duration(total_seconds)
        })



@extend_schema(
    responses=DOWNLOAD_MEDIAFILE_RESPONSE_SCHEMA,
    description="Get a download URL (presigned S3 or local) for a media file."
)
class DownloadMediaFileView(APIView):
    """
    Retrieve a URL for downloading the requested media file.
    If REMOTE_STATIC_FILES is True, it generates a pre-signed URL from S3.
    If REMOTE_STATIC_FILES is False, it returns the local URL of the file.

    GET /api/mediafiles/download/<id>/
    """
    authentication_classes = [KnoxTokenAuthentication]
    permission_classes     = [IsAuthenticated]
    
    def get(self, request, pk, format=None):
        try:
            # Ensure the media file belongs to the current user.
            media_file = MediaFile.objects.get(id=pk, owner=request.user)
        except MediaFile.DoesNotExist:
            return Response({"detail": "Media file not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if we are using remote static files (S3)
        if getattr(settings, 'REMOTE_STATIC_FILES', False):
            try:
                s3_client = boto3.client('s3', region_name=settings.AWS_S3_REGION)
                file_key = media_file.file.name  # The S3 key stored in the file field.
                presigned_url = s3_client.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={
                        'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                        'Key': file_key,
                    },
                    ExpiresIn=3600  # URL valid for 1 hour
                )
                download_url = presigned_url
            except Exception as e:
                return Response({"detail": f"Error generating download URL: {str(e)}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Local storage: use the file's URL provided by Django.
            if media_file.file:
                # Build an absolute URL using the request object.
                download_url = request.build_absolute_uri(media_file.file.url)
            else:
                return Response({"detail": "File not available."},
                                status=status.HTTP_404_NOT_FOUND)

        return Response({"url": download_url}, status=status.HTTP_200_OK)