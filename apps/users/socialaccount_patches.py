from allauth.socialaccount.models import SocialAccount

def patched_socialaccount_str(self):
    return str(self.user)  # Ensure it always returns a string

SocialAccount.__str__ = patched_socialaccount_str