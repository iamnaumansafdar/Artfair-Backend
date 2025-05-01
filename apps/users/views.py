from django.contrib.auth import login
from drf_spectacular.utils import extend_schema
from knox.views import LoginView as KnoxLoginView
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from .serializers import UserChangePasswordSerializer,SendPasswordResetEmailSerializer,UserPasswordResetSerializer,SendOTPSerializer, VerifyOtpSerializer, ResendOtpSerializer, EmptyResponseSerializer
from .renderers import UserRenderer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.mail import send_mail
from django.utils.timezone import now, timedelta
from .models import CustomUser
import random
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from knox.views import LogoutView as KnoxLogoutView
from knox.views import LogoutAllView as KnoxLogoutAllView
from .utils import Util
from twilio.rest import Client
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.utils import OpenApiParameter
from rest_framework.decorators import action

from .schema import (
    LOGIN_RESPONSE_SCHEMA,
    PROFILE_DETAIL_SCHEMA,
    PROFILE_PUT_SCHEMA,
    PROFILE_PATCH_SCHEMA,
    USER_CHANGE_PASSWORD_SCHEMA,
    USER_PASSWORD_RESET_SCHEMA,
    USER_PASSWORD_RESET_SUCCESS_SCHEMA,
    SEND_OTP_SCHEMA,
    VERIFY_OTP_AND_RESET_PASSWORD_SCHEMA,
    SEND_PHONE_OTP_SCHEMA,
    VERIFY_OTP_SCHEMA,
    SIGNUP_VERIFY_SCHEMA, SIGNUP_INITIATE_SCHEMA, SIGNUP_RESEND_OTP_SCHEMA
    
)
from .serializers import (
    AuthTokenSerializer,
    CreateUserSerializer,
    UserProfileSerializer,
    UserLoginStatusSerializer,
)


@extend_schema(responses=LOGIN_RESPONSE_SCHEMA)
class LoginView(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = AuthTokenSerializer

    def post(self, request, format=None) -> Response:
        serializer = AuthTokenSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return super(LoginView, self).post(request, format=None)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@method_decorator(csrf_exempt, name='dispatch')
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

    @extend_schema(responses=PROFILE_DETAIL_SCHEMA)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(responses=PROFILE_PATCH_SCHEMA)
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(responses=PROFILE_PUT_SCHEMA)
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

@extend_schema(responses=LOGIN_RESPONSE_SCHEMA)
class LoginView(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = AuthTokenSerializer

    def post(self, request, format=None) -> Response:
        serializer = AuthTokenSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return super(LoginView, self).post(request, format=None)


@extend_schema(responses=SIGNUP_INITIATE_SCHEMA)
class InitiateSignupView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = CreateUserSerializer

    def perform_create(self, serializer):
        # Save user instance without activating (is_active=False)
        user = serializer.save(is_active=False)

        # Generate OTP
        otp = random.randint(100000, 999999)
        user.OTP = otp
        user.OTP_created_at = now()
        user.save()

        # Send Email
        body = f"Your OTP for signup is {otp}. It is valid for 5 minutes."
        Util.send_email({
            'subject': 'Signup OTP Verification for ArtFair AI',
            'body': body,
            'to_email': user.email,
        })

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({'message': 'OTP sent successfully to your email.'}, status=status.HTTP_200_OK)


@extend_schema(responses=VERIFY_OTP_SCHEMA)
class VerifySignupOtpView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyOtpSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        try:
            user = CustomUser.objects.get(email=email)
            if user.OTP != otp:
                return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
            if now() - user.OTP_created_at > timedelta(minutes=5):
                return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

            # Activate user and clear OTP
            user.is_active = True
            user.is_staff = True
            user.OTP = None
            user.OTP_created_at = None
            user.save()

            return Response({'message': 'OTP verified successfully. User registered.'}, status=status.HTTP_200_OK)

        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        ...


@extend_schema(responses=SIGNUP_RESEND_OTP_SCHEMA)
class ResendOtpView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ResendOtpSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = CustomUser.objects.get(email=email)
            otp = random.randint(100000, 999999)  # Generate a 6-digit OTP
            user.OTP = otp
            user.OTP_created_at = now()
            user.save()

            # Send Email
            body = f"Your OTP for signup is {otp}. It is valid for 5 minutes."
            Util.send_email({
                'subject': 'Signup OTP Resend for ArtFair AI',
                'body': body,
                'to_email': email,
            })

            return Response({'message': 'OTP resent successfully to your email.'}, status=status.HTTP_200_OK)

        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)



class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter

    def post(self, request, *args, **kwargs):
        print("Access token:", request.data.get("access_token"))
        return super().post(request, *args, **kwargs)



@extend_schema(
            request=UserChangePasswordSerializer,
            responses=USER_CHANGE_PASSWORD_SCHEMA,
            description="Change the password of the logged-in user."
        )
class UserChangePasswordView(APIView):
    renderer_classes = [UserRenderer]
    permission_classes = (permissions.IsAuthenticated,)


    def post(self, request, format=None):
        serializer = UserChangePasswordSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save() 
        return Response({'message': 'Password Changed Successfully'}, status=status.HTTP_200_OK)


@extend_schema(
    request=SendPasswordResetEmailSerializer,
    responses=USER_PASSWORD_RESET_SCHEMA,
    description="Send a password reset email to the user."
)
@method_decorator(csrf_exempt, name='dispatch')
class SendPasswordResetEmailView(APIView):
    renderer_classes = [UserRenderer]

    def post(self, request, format=None):
        serializer = SendPasswordResetEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'message': 'Password Reset link send. Please check your Email'}, status=status.HTTP_200_OK)


@extend_schema(
    parameters=[
        OpenApiParameter(name="uid", type=OpenApiTypes.STR, description="User identifier"),
        OpenApiParameter(name="token", type=OpenApiTypes.STR, description="Password reset token"),
    ],
    request=UserPasswordResetSerializer,
    responses=USER_PASSWORD_RESET_SUCCESS_SCHEMA,
    description="Reset the password using UID and Token. This endpoint allows users to set a new password if they have a valid reset token.",
)
class UserPasswordResetView(APIView):
    renderer_classes = [UserRenderer]

    def post(self, request, uid, token, format=None):
        serializer = UserPasswordResetSerializer(data=request.data, context={'uid': uid, 'token': token})
        serializer.is_valid(raise_exception=True)
        return Response({'message': 'Password Reset Successfully'}, status=status.HTTP_200_OK)



@extend_schema(
    description="Send an OTP to the user's registered email address for password reset.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Registered email address",
                    "example": "user@example.com",
                },
            },
            "required": ["email"],
        }
    },
    responses=SEND_OTP_SCHEMA,
)
class SendOtpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        email = request.data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            user = CustomUser.objects.get(email=email)
            otp = random.randint(100000, 999999)  # Generate a 6-digit OTP
            user.OTP = otp
            user.OTP_created_at = timezone.now()
            user.save()
            send_mail(
                subject='Your OTP for Password Reset',
                message=f'Your OTP for password reset is {otp}. It is valid for 5 minutes.',
                from_email='noreply@yourdomain.com',
                recipient_list=[email],
                fail_silently=False,
            )
            return Response({'msg': 'OTP sent to your email'}, status=status.HTTP_200_OK)
        else:
            return Response({'errors': {'email': 'User with this email does not exist'}},
                            status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    description="Verify OTP and reset the password.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Registered email",
                    "example": "user@example.com",
                },
                "otp": {
                    "type": "string",
                    "description": "6-digit OTP received via email",
                    "example": "123456",
                },
                "password": {
                    "type": "string",
                    "description": "New password",
                    "example": "securepassword",
                },
                "password2": {
                    "type": "string",
                    "description": "Confirm new password",
                    "example": "securepassword",
                },
            },
            "required": ["email", "otp", "password", "password2"],
        }
    },
    responses=VERIFY_OTP_AND_RESET_PASSWORD_SCHEMA,
)
class VerifyOtpAndResetPasswordView(APIView):
    permission_classes = [AllowAny]


    def post(self, request, format=None):
        email = request.data.get('email')
        otp = request.data.get('otp')
        password = request.data.get('password')
        password2 = request.data.get('password2')
        if password != password2:
            return Response({'errors': {'password': 'Passwords must match'}},status=status.HTTP_400_BAD_REQUEST)
        else:
            if not CustomUser.objects.filter(email=email).exists():
                return Response({'errors': {'email': 'User with this email does not exist'}},
                                status=status.HTTP_404_NOT_FOUND)

            user = CustomUser.objects.get(email=email)
            otp_entry = user.OTP
            if otp_entry == otp:
                time_diff = timezone.now() - user.OTP_created_at
                if time_diff > timedelta(minutes=5):
                    user.OTP = None
                    user.OTP_created_at = None
                    user.save()
                    return Response({"detail": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)
                if password != password2:
                    return Response({'errors': {'password': 'Password and Confirm Password do not match'}},
                                    status=status.HTTP_400_BAD_REQUEST)
                user.OTP = None
                user.OTP_created_at = None
                user.set_password(password)
                user.save()

                return Response({'msg': 'Password reset successfully'}, status=status.HTTP_200_OK)
            else:
                return Response({'errors': {'otp': 'Invalid or expired OTP'}}, status=status.HTTP_400_BAD_REQUEST)



@extend_schema(
    description="Verify the OTP sent to the phone number and reset the user's password.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": "The user's registered phone number in E.164 format (e.g., +1234567890).",
                    "example": "+1234567890",
                },
                "otp": {
                    "type": "string",
                    "description": "The OTP sent to the user's phone number.",
                    "example": "123456",
                },
                "password": {
                    "type": "string",
                    "description": "The new password for the user.",
                    "example": "securepassword",
                },
                "password2": {
                    "type": "string",
                    "description": "Confirmation of the new password.",
                    "example": "securepassword",
                },
            },
            "required": ["phone_number", "otp", "password", "password2"],
        }
    },
    responses=VERIFY_OTP_SCHEMA,
)



@extend_schema(
   description="Send an OTP to the user's registered phone number.",
   request=SendOTPSerializer,
   responses=SEND_PHONE_OTP_SCHEMA,
)
class SendPhoneOtpView(APIView):
   permission_classes = (permissions.IsAuthenticated,)
  
   def post(self, request, *args, **kwargs):
       serializer = SendOTPSerializer(data=request.data)
       serializer.is_valid(raise_exception=True)
       phone_number = serializer.validated_data['phone_number']
       if not CustomUser.objects.filter(phone_number=phone_number).exists():
           return Response({'errors': {'phone_number': 'User with this phone number does not exist'}},
                           status=status.HTTP_404_NOT_FOUND)


       user = CustomUser.objects.get(phone_number=phone_number)
       otp = random.randint(100000, 999999)
       user.phone_otp = str(otp)
       user.phone_otp_created_at = now()
       user.save()


       client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
       client.messages.create(
           body=f'Your OTP is {otp}',
           from_=settings.TWILIO_PHONE_NUMBER,
           to=phone_number
       )


       return Response({'msg': 'OTP sent successfully'}, status=status.HTTP_200_OK)




@extend_schema(
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,  # Use a generic object if you don’t have a full serializer
            description="OTP verified successfully."
        )
    }
)
class VerifyOTPView(APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        otp = request.data.get('otp')
        password = request.data.get('password')
        password2 = request.data.get('password2')
        if password != password2:
            return Response({'errors': {'password': 'Passwords must match'}}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                return Response({'errors': {'phone_number': 'User not found'}}, status=status.HTTP_404_NOT_FOUND)

            if user.phone_otp == otp:
                if now() - user.phone_otp_created_at > timedelta(minutes=5):
                    user.phone_otp = None
                    user.phone_otp_created_at = None
                    user.save()
                    return Response({'errors': {'otp': 'OTP has expired'}}, status=status.HTTP_400_BAD_REQUEST)


                user.phone_otp = None
                user.phone_otp_created_at = None
                user.set_password(password)
                user.save()

                return Response({'msg': 'OTP verified successfully'}, status=status.HTTP_200_OK)
            else:
                return Response({'errors': {'otp': 'Invalid OTP'}}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(
    responses={
        204: OpenApiResponse(
            response=OpenApiTypes.NONE,   # no content returned; drf-spectacular has an explicit type for that
            description="User logged out successfully."
        )
    },
)
class LogoutView(KnoxLogoutView):
    serializer_class = EmptyResponseSerializer
    pass



@extend_schema(
    responses={
        204: OpenApiResponse(
            response=OpenApiTypes.NONE,
            description="All user sessions logged out successfully."
        )
    },
)
class LogoutAllView(KnoxLogoutAllView):
    serializer_class = EmptyResponseSerializer
    pass


        
    