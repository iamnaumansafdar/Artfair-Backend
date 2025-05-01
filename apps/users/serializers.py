from .models import CustomUser
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework import serializers
from django.conf import settings
from .utils import Util
from django.db import transaction
from apps.training_data.models import Channel, ChannelMember


class AuthTokenSerializer(serializers.Serializer):
    email = serializers.EmailField(label=_("Email"), write_only=True)
    password = serializers.CharField(
        label=_("Password"),
        style={"input_type": "password"},
        trim_whitespace=False,
        write_only=True,
    )
    token = serializers.CharField(label=_("Token"), read_only=True)

    def validate(self, attrs: dict) -> dict:
        email = attrs.get("email")
        password = attrs.get("password")

        # The authenticate call simply returns None for is_active=False users
        if email and password:
            user: CustomUser = authenticate(
                request=self.context.get("request"), email=email, password=password
            )

            if not user:
                msg = _("Unable to log in with provided credentials.")
                raise serializers.ValidationError(msg, code="authorization")
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs


class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'brand_name', 'password']
        extra_kwargs = {'password': {'write_only': True, 'min_length': 6}}

    # atomic so we don’t end up with a user but no channel if something fails
    @transaction.atomic
    def create(self, validated_data: dict) -> CustomUser:
        brand = validated_data.pop("brand_name").strip()
        # 1.create the user (is_active=False set by view)
        user: CustomUser = CustomUser.objects.create_user(**validated_data)
        # 2.create or reuse the Channel
        channel, _ = Channel.objects.get_or_create(title=brand)
        # 3.make the registering user the OWNER of that channel
        ChannelMember.objects.get_or_create(
            channel=channel,
            user=user,
            defaults={"role": ChannelMember.Role.OWNER},
        )
        return user

class VerifyOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    
class ResendOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)

    class Meta:
        fields = ['email']


class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ("email", "password", "first_name", "last_name")
        extra_kwargs = {"password": {"write_only": True, "min_length": 5}}

    def update(self, instance: CustomUser, validated_data: dict) -> CustomUser:
        password = validated_data.pop("password", None)
        user: CustomUser = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user


class LoginResponseSerializer(serializers.Serializer):
    expiry = serializers.DateTimeField()
    token = serializers.CharField()
    user = UserProfileSerializer()

    def get_user(self, obj):
        user = obj.get("user")
        return {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }


class UserChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        max_length=255, style={'input_type': 'password'}, write_only=True
    )
    password = serializers.CharField(max_length=255, style={'input_type': 'password'}, write_only=True)
    password2 = serializers.CharField(max_length=255, style={'input_type': 'password'}, write_only=True)

    class Meta:
        fields = ['old_password', 'password', 'password2']

    def validate(self, attrs):
        old_password = attrs.get('old_password')
        new_password = attrs.get('password')
        confirm_password = attrs.get('password2')
        user = self.context.get('user')

        # Check if the provided old password is correct
        if not user.check_password(old_password):
            raise serializers.ValidationError("Old password is incorrect")

        # Check that the new passwords match
        if new_password != confirm_password:
            raise serializers.ValidationError("Password and Confirm Password doesn't match")

        # Ensure the new password is different from the old password
        if old_password == new_password:
            raise serializers.ValidationError("New password must be different from the old password")

        return attrs

    def save(self, **kwargs):
        user = self.context.get('user')
        user.set_password(self.validated_data['password'])
        user.save()
        return user


class SendPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)

    class Meta:
        fields = ['email']

    def validate(self, attrs):
        email = attrs.get('email')
        if CustomUser.objects.filter(email=email).exists():
            user = CustomUser.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.id))
            token = PasswordResetTokenGenerator().make_token(user)
            # Use FRONTEND_RESET_PASSWORD_URL from settings
            link = f"{settings.FRONTEND_RESET_PASSWORD_URL}/{uid}/{token}/"
            # Send EMail
            body = 'Click Following Link to Reset Your Password ' + link
            data = {
                'subject': 'Reset Your Password',
                'body': body,
                'to_email': user.email
            }
            Util.send_email(data)
            return attrs
        else:
            raise serializers.ValidationError('You are not a Registered User')


class UserPasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=255, style={'input_type': 'password'}, write_only=True)
    password2 = serializers.CharField(max_length=255, style={'input_type': 'password'}, write_only=True)

    class Meta:
        fields = ['password', 'password2']

    def validate(self, attrs):
        try:
            password = attrs.get('password')
            password2 = attrs.get('password2')
            uid = self.context.get('uid')
            token = self.context.get('token')
            if password != password2:
                raise serializers.ValidationError("Password and Confirm Password doesn't match")
            id = smart_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(id=id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise serializers.ValidationError('Token is not Valid or Expired')
            user.set_password(password)
            user.save()
            return attrs
        except DjangoUnicodeDecodeError as identifier:
            PasswordResetTokenGenerator().check_token(user, token)
            raise serializers.ValidationError('Token is not Valid or Expired')


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        from phonenumbers import parse, is_valid_number, format_number, PhoneNumberFormat
        try:
            phone = parse(value, None)
            if not is_valid_number(phone):
                raise serializers.ValidationError("Invalid phone number")
            return format_number(phone, PhoneNumberFormat.E164)
        except Exception:
            raise serializers.ValidationError("Invalid phone number format")


class EmptyResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)

class UserLoginStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("id", "email")