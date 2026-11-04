from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.accounts.models import GymBranch

class Attendance(models.Model):
    class CheckInMethod(models.TextChoices):
        QR_CODE = 'QR_CODE', 'QR Code Scan'
        MANUAL_STAFF = 'MANUAL_STAFF', 'Staff Manual'
        BIOMETRIC = 'BIOMETRIC', 'Biometric / RFID'
        MOBILE_APP = 'MOBILE_APP', 'Mobile App'

    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Checked In (Active)'
        CHECKED_OUT = 'CHECKED_OUT', 'Completed (Checked Out)'

    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    branch = models.ForeignKey(
        GymBranch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branch_attendances'
    )
    date = models.DateField(default=timezone.now, db_index=True)
    check_in_time = models.DateTimeField(default=timezone.now)
    check_out_time = models.DateTimeField(null=True, blank=True)
    method = models.CharField(
        max_length=20,
        choices=CheckInMethod.choices,
        default=CheckInMethod.QR_CODE
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_attendances'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT
    )

    class Meta:
        ordering = ['-date', '-check_in_time']
        unique_together = ('member', 'date')
        verbose_name = 'Attendance Log'
        verbose_name_plural = 'Attendance Logs'

    def __str__(self):
        return f"{self.member.full_name} - {self.date} ({self.get_status_display()})"

    @property
    def duration_minutes(self):
        if self.check_out_time and self.check_in_time:
            delta = self.check_out_time - self.check_in_time
            return max(0, int(delta.total_seconds() / 60))
        return None
