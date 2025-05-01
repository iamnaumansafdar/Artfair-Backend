from drf_spectacular.utils import OpenApiExample, OpenApiResponse

from apps.core.schema import UNAUTHORIZED_EXAMPLES, ErrorResponseSerializer

from .serializers import (
    LoginResponseSerializer,
    UserProfileSerializer,
)

LOGIN_RESPONSE_SCHEMA = {
    200: OpenApiResponse(
        response=LoginResponseSerializer,
        description="Successfully authenticated",
    ),
    400: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Invalid credentials",
        examples=[
            OpenApiExample(
                "Invalid Credentials",
                value={"detail": "Unable to log in with provided credentials."},
                status_codes=["400"],
            ),
            OpenApiExample(
                "Missing Fields",
                value={
                    "email": ["This field is required."],
                    "password": ["This field is required."],
                },
                status_codes=["400"],
            ),
        ],
    ),
}

# Schema for Signup Initiation
SIGNUP_INITIATE_SCHEMA = {
    200: OpenApiResponse(
        description="OTP sent successfully.",
        examples=[
            OpenApiExample(
                "Success",
                value={"message": "OTP sent successfully."},
                status_codes=["200"],
            ),
        ],
    ),
    400: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Validation error",
        examples=[
            OpenApiExample(
                "Missing Fields",
                value={"email": ["This field is required."]},
                status_codes=["400"],
            ),
        ],
    ),
}

# Schema for Verify OTP
SIGNUP_VERIFY_SCHEMA = {
    200: OpenApiResponse(
        description="User registered successfully.",
        examples=[
            OpenApiExample(
                "Success",
                value={"message": "User registered successfully."},
                status_codes=["200"],
            ),
        ],
    ),
    400: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Validation error",
        examples=[
            OpenApiExample(
                "Invalid OTP",
                value={"error": "Invalid OTP"},
                status_codes=["400"],
            ),
            OpenApiExample(
                "OTP Expired",
                value={"error": "OTP has expired"},
                status_codes=["400"],
            ),
        ],
    ),
}

# Schema for Resend OTP
SIGNUP_RESEND_OTP_SCHEMA = {
    200: OpenApiResponse(
        description="OTP resent successfully.",
        examples=[
            OpenApiExample(
                "Success",
                value={"message": "OTP resent successfully."},
                status_codes=["200"],
            ),
        ],
    ),
    404: OpenApiResponse(
        description="User not found.",
        examples=[
            OpenApiExample(
                "User Not Found",
                value={"error": "User not found."},
                status_codes=["404"],
            ),
        ],
    ),
}



PROFILE_DETAIL_SCHEMA = {
    200: OpenApiResponse(
        response=UserProfileSerializer,
        description="User profile data",
    ),
    401: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Authentication required",
        examples=UNAUTHORIZED_EXAMPLES,
    ),
}

PROFILE_PUT_SCHEMA = {
    200: OpenApiResponse(
        response=UserProfileSerializer,
        description="User profile updated",
    ),
    400: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Validation error",
        examples=[
            OpenApiExample(
                "Invalid Data",
                value={"password": ["Password must be at least 5 characters long."]},
                status_codes=["400"],
            ),
            OpenApiExample(
                "Missing Fields",
                value={"password": ["This field is required."]},
                status_codes=["400"],
            ),
        ],
    ),
    401: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Authentication required",
        examples=UNAUTHORIZED_EXAMPLES,
    ),
}

PROFILE_PATCH_SCHEMA = {
    200: OpenApiResponse(
        response=UserProfileSerializer,
        description="User profile updated",
    ),
    401: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Authentication required",
        examples=UNAUTHORIZED_EXAMPLES,
    ),
}


USER_CHANGE_PASSWORD_SCHEMA = {
    200: OpenApiResponse(
        description="Password Changed Successfully",
        examples=[
            OpenApiExample(
                "Success",
                value={"msg": "Password Changed Successfully"},
                status_codes=["200"],
            ),
        ],
    ),
    400: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Validation error",
        examples=[
            OpenApiExample(
                "Passwords do not match",
                value={
                    "non_field_errors": [
                        "Password and Confirm Password doesn't match"
                    ]
                },
                status_codes=["400"],
            ),
            OpenApiExample(
                "Missing Fields",
                value={
                    "password": ["This field is required."],
                    "password2": ["This field is required."],
                },
                status_codes=["400"],
            ),
        ],
    ),
    401: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Authentication required",
        examples=UNAUTHORIZED_EXAMPLES,
    ),
}


USER_PASSWORD_RESET_SCHEMA = {
    200: OpenApiResponse(
        description="Password Reset Link Sent",
        examples=[
            OpenApiExample(
                "Success",
                value={"message": "Password Reset link sent. Please check your Email."},
                status_codes=["200"],
            ),
        ],
    ),
    400: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Validation error",
        examples=[
            OpenApiExample(
                "Invalid Email",
                value={"email": ["You are not a Registered User"]},
                status_codes=["400"],
            ),
            OpenApiExample(
                "Missing Fields",
                value={"email": ["This field is required."]},
                status_codes=["400"],
            ),
        ],
    ),
    401: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Authentication required",
        examples=UNAUTHORIZED_EXAMPLES,
    ),
}

USER_PASSWORD_RESET_SUCCESS_SCHEMA = {
    200: OpenApiResponse(
        description="Password Reset Successful",
        examples=[
            OpenApiExample(
                "Success",
                value={"message": "Password Reset Successfully"},
                status_codes=["200"],
            ),
        ],
    ),
    400: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Validation error",
        examples=[
            OpenApiExample(
                "Invalid Token or Password",
                value={
                    "non_field_errors": ["Token is not Valid or Expired"],
                },
                status_codes=["400"],
            ),
            OpenApiExample(
                "Passwords do not match",
                value={
                    "non_field_errors": ["Password and Confirm Password doesn't match"],
                },
                status_codes=["400"],
            ),
            OpenApiExample(
                "Missing Fields",
                value={
                    "password": ["This field is required."],
                    "password2": ["This field is required."],
                },
                status_codes=["400"],
            ),
        ],
    ),
    401: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Authentication required",
        examples=UNAUTHORIZED_EXAMPLES,
    ),
}


SEND_OTP_SCHEMA = {
    200: OpenApiResponse(
        description="OTP sent successfully",
        examples=[
            OpenApiExample(
                "Success",
                value={"msg": "OTP sent to your email"},
                status_codes=["200"],
            ),
        ],
    ),
    404: OpenApiResponse(
        description="User with this email does not exist",
        examples=[
            OpenApiExample(
                "Error",
                value={"errors": {"email": "User with this email does not exist"}},
                status_codes=["404"],
            ),
        ],
    ),
}


VERIFY_OTP_AND_RESET_PASSWORD_SCHEMA = {
    200: OpenApiResponse(
        description="Password reset successfully",
        examples=[
            OpenApiExample(
                "Success",
                value={"msg": "Password reset successfully"},
                status_codes=["200"],
            ),
        ],
    ),
    400: OpenApiResponse(
        description="Validation error",
        examples=[
            OpenApiExample(
                "Password Mismatch",
                value={"errors": {"password": "Passwords must match"}},
                status_codes=["400"],
            ),
            OpenApiExample(
                "Invalid OTP",
                value={"errors": {"otp": "Invalid or expired OTP"}},
                status_codes=["400"],
            ),
            OpenApiExample(
                "Expired OTP",
                value={"detail": "OTP has expired."},
                status_codes=["400"],
            ),
            OpenApiExample(
                "Missing Fields",
                value={
                    "email": ["This field is required."],
                    "otp": ["This field is required."],
                    "password": ["This field is required."],
                    "password2": ["This field is required."],
                },
                status_codes=["400"],
            ),
        ],
    ),
    404: OpenApiResponse(
        description="User not found",
        examples=[
            OpenApiExample(
                "Email Not Found",
                value={"errors": {"email": "User with this email does not exist"}},
                status_codes=["404"],
            ),
        ],
    ),
}


SEND_PHONE_OTP_SCHEMA = {
    200: OpenApiResponse(
        description="OTP sent successfully",
        examples=[
            OpenApiExample(
                "Success",
                value={"msg": "OTP sent successfully"},
                status_codes=["200"],
            ),
        ],
    ),
    404: OpenApiResponse(
        description="User with this phone number does not exist",
        examples=[
            OpenApiExample(
                "Phone Number Not Found",
                value={"errors": {"phone_number": "User with this phone number does not exist"}},
                status_codes=["404"],
            ),
        ],
    ),
    400: OpenApiResponse(
        description="Validation error",
        examples=[
            OpenApiExample(
                "Invalid Format",
                value={"errors": {"phone_number": "Invalid phone number format"}},
                status_codes=["400"],
            ),
        ],
    ),
}

VERIFY_OTP_SCHEMA = {
    200: OpenApiResponse(
        description="OTP verified successfully, and the password has been reset.",
        examples=[
            OpenApiExample(
                "Success",
                value={"msg": "OTP verified successfully"},
                status_codes=["200"],
            ),
        ],
    ),
    400: OpenApiResponse(
        description="Validation error",
        examples=[
            OpenApiExample(
                "Invalid OTP",
                value={"errors": {"otp": "Invalid OTP"}},
                status_codes=["400"],
            ),
            OpenApiExample(
                "OTP Expired",
                value={"errors": {"otp": "OTP has expired"}},
                status_codes=["400"],
            ),
            OpenApiExample(
                "Password Mismatch",
                value={"errors": {"password": "Passwords must match"}},
                status_codes=["400"],
            ),
        ],
    ),
    404: OpenApiResponse(
        description="User not found",
        examples=[
            OpenApiExample(
                "Phone Number Not Found",
                value={"errors": {"phone_number": "User not found"}},
                status_codes=["404"],
            ),
        ],
    ),
}