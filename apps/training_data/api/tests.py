from apps.testing.testcase import TestCase 
from apps.training_data.models import MediaFile

MEDIA_FILE_CREATE_API = "/training_data/create/"
GET_ORPHAN_FILES_API = "/training_data/get_orphan_files/{}/"

class TestApiTests(TestCase):

    def setUp(self):
        self.user, self.client = self.create_user_and_client()
        self.payload = [
            {
                "user_email": self.user.email,
                "original_filename": "file1.txt",
                "fileType": "audio/aac",
                "fileSize": 1234,
                "isSourceFile": True,
                "processing_status": "complete",
                "s3_url": "https://your-bucket.s3.amazonaws.com/uploads/file1.txt",
                "description": "Test file 1",
                "license_content_agreed": True,
                "md5Hash": "d41d8cd98f00b204e9800998ecf8427e"
            },
            {
                "user_email": self.user.email,
                "original_filename": "file2.txt",
                "fileType": "audio/aac",
                "fileSize": 4321,
                "isSourceFile": False,
                "processing_status": "complete",
                "s3_url": "https://your-bucket.s3.amazonaws.com/uploads/file2.txt",
                "description": "Test file 2",
                "license_content_agreed": False,
                "md5Hash": "d41d8cd98f00b204e9800998ecf0135e",
            }
        ]

    def test_create_media_file(self): 
        response = self.client.post(MEDIA_FILE_CREATE_API, data=self.payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(MediaFile.objects.count(), 2)

        res_data = response.json()
        expected_keys = {"original_filename", "processing_status", "linked_video_matched", "file_size", "created_at"} 
        self.assertEqual(set(res_data[0].keys()), expected_keys) 

    def test_get_orphan_files_by_user(self):
        response = self.client.get(GET_ORPHAN_FILES_API.format(self.user.id))
        # self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["orphan_files"], [])
        # Create media files for the user
        self.client.post(MEDIA_FILE_CREATE_API, data=self.payload, format="json")
        response = self.client.get(GET_ORPHAN_FILES_API.format(self.user.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["orphan_files"]), 2)

        