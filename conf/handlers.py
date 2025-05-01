from django.utils.log import AdminEmailHandler
import logging

class ForceAdminEmailHandler(AdminEmailHandler):
    def format_subject(self, record):
        try:
            subject = "Error: " + record.getMessage()
            return subject.replace("\n", "\\n").replace("\r", "\\r")
        except Exception as e:
            return "Error: (subject formatting failed)"

    def send_mail(self, subject, message, fail_silently=False):
        try:
            from django.core.mail import mail_admins
            mail_admins(subject, message, fail_silently=fail_silently)
        except Exception as e:
            logging.getLogger(__name__).error("Error sending admin email: %s", e)

    def emit(self, record):
        try:
            subject = self.format_subject(record)
            message = self.format(record)
            self.send_mail(subject, message, fail_silently=True)
        except Exception:
            self.handleError(record)


