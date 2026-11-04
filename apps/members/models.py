import uuid
import io
import qrcode
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from apps.accounts.models import GymOrganization, GymBranch

class Member(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        EXPIRED = 'EXPIRED', 'Expired'
        PENDING = 'PENDING', 'Pending Verification'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='member_profile'
    )
    organization = models.ForeignKey(
        GymOrganization,
        on_delete=models.CASCADE,
        related_name='members'
    )
    branch = models.ForeignKey(
        GymBranch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )
    member_id = models.CharField(max_length=50, unique=True, db_index=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True, default='')
    emergency_contact_phone = models.CharField(max_length=20, blank=True, default='')
    blood_group = models.CharField(max_length=10, blank=True, default='')
    medical_history = models.TextField(blank=True, default='')
    fitness_goals = models.TextField(blank=True, default='')
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_code = models.ImageField(upload_to='members/qr_codes/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    joined_date = models.DateField(default=timezone.now)
    assigned_trainer = models.ForeignKey(
        'trainers.Trainer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_members'
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-joined_date', '-id']
        verbose_name = 'Gym Member'
        verbose_name_plural = 'Gym Members'

    def __str__(self):
        return f"{self.full_name} ({self.member_id})"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def email(self):
        return self.user.email

    @property
    def phone(self):
        return self.user.phone

    @property
    def current_membership(self):
        return self.memberships.filter(status='ACTIVE').order_by('-end_date').first()

    @property
    def is_membership_active(self):
        membership = self.current_membership
        if membership:
            return membership.is_currently_active
        return False

    @property
    def days_until_expiry(self):
        membership = self.current_membership
        if membership:
            return membership.days_remaining
        return 0

    def generate_qr_code(self):
        qr_data = f"FITNOVA:{self.member_id}:{self.qr_token}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#172554", back_color="#FFFFFF")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        filename = f"qr_{self.member_id}.png"
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)
