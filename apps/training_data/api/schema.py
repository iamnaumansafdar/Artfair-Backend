from drf_spectacular.utils import OpenApiResponse, OpenApiExample
from .serializers import *

CAPTION_FILE_LIST_RESPONSE_SCHEMA = {
    200: OpenApiResponse(
        response=CaptionFileSerializer,
        description="List of caption files for the current user (each item contains S3 URL and metadata).",
        examples=[
            OpenApiExample(
                "Caption Files Example",
                value=[
                    {
                        "id": 1,
                        "original_filename": "example_caption.ass",
                        "file_type": "ass",
                        "S3URL": "https://s3.amazonaws.com/yourbucket/uploads/1/mediafile/example_caption.ass"
                    }
                ],
                status_codes=["200"],
            )
        ]
    ),
}



MEDIAFILE_LIST_RESPONSE_SCHEMA = {
    200: OpenApiResponse(
        response=MediaFileSerializer,
        description="List of media files for the current user, with linked file and owner info.",
        examples=[
            OpenApiExample(
                "Full Media File Example",
                value=[
                    {
                        "id": 21,
                        "owner": {
                            "id": 1,
                            "email": "admin@admin.com",
                            "first_name": "",
                            "last_name": ""
                        },
                        "linked_video_matched": True,
                        "original_filename": "SheetPro.MP4",
                        "file_type": "video",
                        "linked_file": {
                            "id": 19,
                            "original_filename": "20241215_EDIT_SilentHill2.ass",
                            "S3URL": "http://127.0.0.1:8000/media/media/20241215_EDIT_SilentHill2.ass",
                            "file_type": None
                        },
                        "S3URL": "http://127.0.0.1:8000/media/media/SheetPro.MP4",
                        "file_size": "0 bytes",
                        "md5_hash": None,
                        "processing_status": "failed",
                        "metadata": {
                            "error": "The '_metadata_file' attribute has no file associated with it."
                        },
                        "is_source_file": False,
                        "description": "",
                        "license_content_agreed": False,
                        "created_at": "2025-03-04 07:22",
                        "updated_at": "2025-03-04 07:22"
                    }
                ],
                status_codes=["200"],
            )
        ]
    )
}



SPEAKER_LIST_RESPONSE_SCHEMA = {
    200: OpenApiResponse(
        response=SpeakerSerializer,
        description="List of speakers for the current user, including speaker attributes and associated media file IDs.",
        examples=[
            OpenApiExample(
                "Speaker Example",
                value=[
                    {
                        "id": 1,
                        "speaker_id": "abcd-1234",
                        "name": "John Doe",
                        "primary_language": "English",
                        "dob": "1990-01-01",
                        "gender": "Male",
                        "owner": 1,
                        "media_files": [10, 12],
                        "extra_metadata": {},
                        "created_at": "2025-04-08T00:00:00Z",
                        "updated_at": "2025-04-08T00:00:00Z"
                    }
                ],
                status_codes=["200"]
            )
        ]
    ),
}


TOTAL_VIDEO_HOURS_RESPONSE_SCHEMA = {
    200: OpenApiResponse(
        response=TotalVideoHoursSerializer,
        description="Returns the count of videos and their combined duration (or single video duration).",
        examples=[
            OpenApiExample(
                "All Videos Combined",
                value={
                    "video_count": 5,
                    "total_hours": "12:34:56"
                },
                status_codes=["200"],
            ),
            OpenApiExample(
                "Single Video",
                value={
                    "video_count": 1,
                    "total_hours": "02:15:30"
                },
                status_codes=["200"],
            ),
        ],
    ),
    400: OpenApiResponse(
        description="Bad request (e.g. non-video file_id was provided)."
    ),
    404: OpenApiResponse(
        description="Not found (e.g. video_id doesn’t exist or doesn’t belong to user)."
    ),
}

DOWNLOAD_MEDIAFILE_RESPONSE_SCHEMA = {
    200: OpenApiResponse(
        response=DownloadUrlSerializer,
        description="A URL where the client can download the file (either a presigned S3 URL or a local media URL).",
        examples=[
            OpenApiExample(
                "S3 Presigned URL",
                value={"url": "https://bucket.s3.amazonaws.com/path/to/file.mp4?X-Amz-..."},
                status_codes=["200"],
            ),
            OpenApiExample(
                "Local URL",
                value={"url": "http://localhost:8000/media/uploads/.../file.mp4"},
                status_codes=["200"],
            ),
        ],
    ),
    404: OpenApiResponse(description="Media file not found or not owned by the user."),
    500: OpenApiResponse(description="Error generating the download URL."),
}