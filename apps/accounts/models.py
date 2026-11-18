import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class GymOrganization(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    logo = models.ImageField(upload_to='organizations/logos/', null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    website = models.URLField(blank=True, default='')
    tax_id = models.CharField(max_length=50, blank=True, default='', verbose_name='Tax/GST ID')
    currency = models.CharField(max_length=10, default='$')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Gym Organization'
        verbose_name_plural = 'Gym Organizations'
        ordering = ['name']

    def __str__(self):
        return self.name


class GymBranch(models.Model):
    organization = models.ForeignKey(GymOrganization, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, default='')
    manager_name = models.CharField(max_length=150, blank=True, default='')
    is_main_branch = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Gym Branch'
        verbose_name_plural = 'Gym Branches'
        ordering = ['organization', 'name']

    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', _('Super Admin')
        GYM_ADMIN = 'GYM_ADMIN', _('Gym Admin')
        STAFF = 'STAFF', _('Receptionist / Staff')
        TRAINER = 'TRAINER', _('Trainer')
        MEMBER = 'MEMBER', _('Gym Member')

    class Gender(models.TextChoices):
        MALE = 'MALE', _('Male')
        FEMALE = 'FEMALE', _('Female')
        OTHER = 'OTHER', _('Other')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        db_index=True
    )
    organization = models.ForeignKey(
        GymOrganization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users'
    )
    branch = models.ForeignKey(
        GymBranch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branch_users'
    )
    phone = models.CharField(max_length=20, blank=True, default='')
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.MALE)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True, default='')
    is_verified = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['organization', 'role']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        full = self.get_full_name()
        return f"{full if full else self.username} ({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN or self.is_superuser

    @property
    def is_gym_admin(self):
        return self.role in [self.Role.SUPER_ADMIN, self.Role.GYM_ADMIN] or self.is_superuser

    @property
    def is_staff_member(self):
        return self.role in [self.Role.SUPER_ADMIN, self.Role.GYM_ADMIN, self.Role.STAFF] or self.is_staff

    @property
    def is_trainer(self):
        return self.role == self.Role.TRAINER

    @property
    def is_member(self):
        return self.role == self.Role.MEMBER

    @property
    def has_face_enrolled(self):
        return hasattr(self, 'face_auth_profile') and self.face_auth_profile.is_active and bool(
            self.face_auth_profile.feature_vector or self.face_auth_profile.encrypted_template
        )


class UserFaceProfile(models.Model):
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='face_auth_profile'
    )
    face_image = models.ImageField(upload_to='users/faces/', blank=True, null=True)
    face_descriptor = models.TextField(blank=True, default='')  # JSON float array from client face-api
    feature_vector = models.TextField(blank=True, default='')   # Plaintext / legacy JSON 128-D float vector
    encrypted_template = models.TextField(blank=True, default='') # AES-256 Fernet-encrypted biometric payload
    face_hash = models.CharField(max_length=64, blank=True, default='', db_index=True) # SHA-256 for duplicate detection
    quality_score = models.FloatField(default=0.0)
    sample_count = models.IntegerField(default=1)
    liveness_verified = models.BooleanField(default=True)
    enrolled_at = models.DateTimeField(auto_now=True)
    last_authenticated_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'User Face Profile'
        verbose_name_plural = 'User Face Profiles'

    def __str__(self):
        return f"Face Profile: {self.user.get_full_name() or self.user.username}"


class FaceAuthenticationLog(models.Model):
    class EventType(models.TextChoices):
        SUCCESS = 'SUCCESS', _('Successful Authentication')
        UNKNOWN_FACE = 'UNKNOWN_FACE', _('Unknown Face (Unregistered)')
        LIVENESS_FAILED = 'LIVENESS_FAILED', _('Liveness Detection Failed')
        SPOOF_SUSPECTED = 'SPOOF_SUSPECTED', _('Potential Spoof / Replay Attack')
        RATE_LIMITED = 'RATE_LIMITED', _('Rate Limit Exceeded')
        ACCOUNT_LOCKED = 'ACCOUNT_LOCKED', _('Account Locked')
        DUPLICATE_ATTEMPT = 'DUPLICATE_ATTEMPT', _('Duplicate Face Registration Attempt')
        CHALLENGE_FAILED = 'CHALLENGE_FAILED', _('Liveness Challenge Failed')

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='face_auth_logs'
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices, db_index=True)
    status = models.CharField(max_length=20, default='DENIED')
    similarity_score = models.FloatField(default=0.0)
    liveness_score = models.FloatField(default=0.0)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_agent = models.TextField(blank=True, default='')
    failure_reason = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Face Authentication Log'
        verbose_name_plural = 'Face Authentication Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.event_type}] {self.status} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"


class FailedLoginAttempt(models.Model):
    ip_address = models.GenericIPAddressField(db_index=True)
    identifier = models.CharField(max_length=150, blank=True, default='', db_index=True)
    attempt_count = models.IntegerField(default=1)
    is_locked = models.BooleanField(default=False)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Failed Login Attempt'
        verbose_name_plural = 'Failed Login Attempts'
        unique_together = ('ip_address', 'identifier')

    def __str__(self):
        return f"{self.identifier} ({self.ip_address}): {self.attempt_count} attempts"


class EmailVerificationOTP(models.Model):
    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Email OTP Verification'
        verbose_name_plural = 'Email OTP Verifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.email} ({'Verified' if self.is_verified else 'Pending'})"


