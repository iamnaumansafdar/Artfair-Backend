from apps.training_data.models import MediaFile
from django.core.mail import send_mail
from django.conf import settings
from celery import Task
from django.core.mail import get_connection, EmailMessage


class SuccessEmailTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        # For testing, we hard-code the recipient.
        try:
            # Assume the first argument is media_file_id
            media_file_id = args[0]
            print(media_file_id, 'media_file_id')
            media_file = MediaFile.objects.get(id=media_file_id)
            print(media_file, 'media_file')
            recipient_email = media_file.owner.email
            print(recipient_email, 'recipient_email')
        except Exception:
            recipient_email = None
        if recipient_email:
            # Force a new connection:
            connection = get_connection(backend=settings.EMAIL_BACKEND, fail_silently=False)
            # Open a new connection explicitly.
            connection.open()
            # Create the email message.
            email = EmailMessage(
                subject="Task Completed Successfully",
                body=f"Task {task_id} completed with result: {retval}",
                from_email=settings.EMAIL_HOST_USER,
                to=[recipient_email],
                connection=connection,
            )
            email.send()
            connection.close()