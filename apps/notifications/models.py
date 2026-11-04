from django.db import models
from django.conf import settings

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        INFO = 'INFO', 'Information'
        WARNING = 'WARNING', 'Warning'
        SUCCESS = 'SUCCESS', 'Success'
        DANGER = 'DANGER', 'Urgent / Alert'
        PAYMENT = 'PAYMENT', 'Payment Received'
        EXPIRY = 'EXPIRY', 'Membership Expiry'
        ATTENDANCE = 'ATTENDANCE', 'Attendance Alert'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    is_read = models.BooleanField(default=False, db_index=True)
    action_url = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.title} -> {self.recipient.username}"

