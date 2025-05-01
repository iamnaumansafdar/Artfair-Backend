from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    # Display all fields in the list view
    list_display = (
        "email",
        "name",
        "brand_name",
        "phone_number",
        "is_scientist",
        "is_staff",
        "is_active",
        "created_at",
        "updated_at",
    )

    # Add all fields to the filter options
    list_filter = (
        "email",
        "is_scientist",
        "is_staff",
        "is_active",
        "created_at",
        "updated_at",
    )

    # Display fields in the detailed view
    fieldsets = (
        (None, {"fields": ("email", "password", "name", "brand_name", "phone_number")}),
        (
            "OTP Information",
            {"fields": ("OTP", "OTP_created_at", "phone_otp", "phone_otp_created_at")},
        ),
        (
            "Permissions",
            {"fields": ("is_staff", "is_active", "groups", "user_permissions")},
        ),
        # (
        #     "Tokens",
        #     {"fields": ("access_token", "refresh_token")},
        # ),
    )

    # Add read-only fields to the detailed view
    readonly_fields = ("created_at", "updated_at")

    # Add all fields to the form used when creating a user
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "name",
                    "brand_name",
                    "phone_number",
                    "is_staff",
                    "is_active",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )

    # Add search capability for email, name, and phone number
    search_fields = ("email", "name", "phone_number")
    ordering = ("email",)


admin.site.register(CustomUser, CustomUserAdmin)
