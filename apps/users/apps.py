from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    
    def ready(self):
        from allauth.socialaccount.models import SocialAccount
        def patched_socialaccount_str(self):
            return str(self.user)
        SocialAccount.__str__ = patched_socialaccount_str

