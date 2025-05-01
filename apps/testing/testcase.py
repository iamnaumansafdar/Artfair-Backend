from django.test import TestCase as DjangoTestCase
from rest_framework.test import APIClient 
from apps.users.models import CustomUser 


class TestCase(DjangoTestCase):

    @property
    def anonymous_client(self):
        """
        This getter method is a singleton for the anonymous client.
        """
        if hasattr(self, "_anonymous_client"):
            return self._anonymous_client
        self._anonymous_client = APIClient()
        return self._anonymous_client
    
    def create_user(self, email=None, password=None):
        if password is None:
            password = "test_password"
        
        if email is None:
            email = "test_user@example.com"
        
        return CustomUser.objects.create_user(
            email=email,
            password=password,
        )

    def create_user_and_client(self, *args, **kwargs):
        user = self.create_user()
        client = APIClient()
        client.force_authenticate(user=user) 
        return user, client 


