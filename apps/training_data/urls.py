from rest_framework.routers import DefaultRouter
from django.urls import path
from .api.views import (
    generate_s3_presigned_url, 
    create_file_upload,
    get_orphan_files,
    create_s3_multipart,
    s3_multipart_listParts,
    s3_multipart_signPart,
    s3_multipart_abort,
    s3_multipart_complete,
    SpeakerViewSet,
    list_media_files,
    ListUserCaptionFilesAPIView,
    MediaFilePartialUpdateView,
    DownloadMediaFileView,
    TotalVideoHoursView
)

router = DefaultRouter()
router.register(r'speakers', SpeakerViewSet, basename='speakers')

urlpatterns = [
    path('generate-s3-presigned-url/',generate_s3_presigned_url, name='generate_s3_presigned_url'),
    path('create/', create_file_upload, name='create_file_upload'),
    path('get_orphan_files/<str:user_email>/', get_orphan_files, name='get_orphan_files'),
    path('create_s3_multipart/', create_s3_multipart, name='create_s3_multipart'),
    path('s3_multipart_listParts/<str:uploadId>/', s3_multipart_listParts, name='s3_multipart_listParts'),
    path('s3_multipart_signPart/<str:uploadId>/<int:partNumber>/', s3_multipart_signPart, name='s3_multipart_signPart'),
    path('s3_multipart_abort/<str:uploadId>/', s3_multipart_abort, name='s3_multipart_abort'),
    path('s3_multipart_complete/<str:uploadId>/', s3_multipart_complete, name='s3_multipart_complete'),

    #Fetch Caption File API
    path('caption-files/', ListUserCaptionFilesAPIView.as_view(), name='list-user-caption-files'),
    path('mediafiles/', list_media_files, name='mediafile-list'),
    path('mediafiles/<int:pk>/', MediaFilePartialUpdateView.as_view(), name='mediafile-update'),
    path('mediafiles/video-hours/', TotalVideoHoursView.as_view(), name='total-video-hours'),
    path('mediafiles/download/<int:pk>/', DownloadMediaFileView.as_view(), name='mediafile-download'),

]

urlpatterns += router.urls