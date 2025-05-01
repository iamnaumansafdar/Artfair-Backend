from django.urls import path, include

from knox import views as knox_views

from .views import *

app_name = "users"


Social = [

    path('social/facebook/', FacebookLogin.as_view(), name='fb_login'),  # Facebook Login
    path('social/google/', GoogleLogin.as_view(), name='google_login'), #google
    path('accounts/', include('allauth.urls')),  # Required for django-allauth
]


CustomUser = [
    path('signup/initiate/', InitiateSignupView.as_view(), name='signup_initiate'),
    path('signup/verify/', VerifySignupOtpView.as_view(), name='signup_verify'),
    path('signup/resend-otp/', ResendOtpView.as_view(), name='resend_otp'),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("login/", LoginView.as_view(), name="knox_login"),
    path('changepassword/', UserChangePasswordView.as_view(), name='changepassword'),
    path('send-reset-password-email/', SendPasswordResetEmailView.as_view(), name='send-reset-password-email'),
    path('reset-password/<str:uid>/<str:token>/', UserPasswordResetView.as_view(), name='reset-password'),
    path('send-otp-email/', SendOtpView.as_view(), name='send_otp'),
    path('send-otp-phone/', SendPhoneOtpView.as_view(), name='send_otp'),
    path('verify-otp-reset-password/', VerifyOtpAndResetPasswordView.as_view(), name='verify_otp_reset_password'),
    path('verify-otp-phone/', VerifyOTPView.as_view(), name='verify_otp'),
    path("logout/", LogoutView.as_view(), name="knox_logout"),
    path("logoutall/", LogoutAllView.as_view(), name="knox_logoutall"),
]

urlpatterns = Social + CustomUser