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
