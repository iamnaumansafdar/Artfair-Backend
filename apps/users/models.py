from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager
from phonenumber_field.modelfields import PhoneNumberField

class TimestampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CustomUser(AbstractUser, TimestampMixin):
    """
    CustomUser is a custom user model that extends Django's AbstractUser.
    It uses email as the unique identifier instead of the username.
    """

    # The username field is set to None to disable it.
    username = None

    # The email field is set to be unique because it is the unique identifier.
    email = models.EmailField(_("email address"), unique=True)
    name = models.CharField(max_length=200, null=True,blank=True)
    brand_name = models.CharField(max_length=150, null=True, blank=True)
    is_scientist = models.BooleanField(default=False)
    OTP = models.CharField(max_length=50,null=True,blank=True)
    OTP_created_at = models.DateTimeField(null=True,blank=True)
    phone_number = PhoneNumberField(unique=True, null=True, blank=True)
    phone_otp = models.CharField(max_length=6, null=True, blank=True)
    phone_otp_created_at = models.DateTimeField(null=True, blank=True)
    access_token = models.CharField(max_length=500, null=True, blank=True)
    refresh_token = models.CharField(max_length=500, null=True, blank=True)

    # Specifies the field to be used as the unique identifier for the user.
    USERNAME_FIELD = "email"
    
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.email
    
    @property
    def all_speakers(self):
        return self.speakers.all()