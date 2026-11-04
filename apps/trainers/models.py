from django.db import models
from django.conf import settings
from apps.accounts.models import GymOrganization, GymBranch

class Trainer(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        ON_LEAVE = 'ON_LEAVE', 'On Leave'
        INACTIVE = 'INACTIVE', 'Inactive'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trainer_profile'
    )
    organization = models.ForeignKey(
        GymOrganization,
        on_delete=models.CASCADE,
        related_name='trainers'
    )
    branch = models.ForeignKey(
        GymBranch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trainers'
    )
    employee_id = models.CharField(max_length=50, unique=True)
    specialization = models.CharField(max_length=200, default='General Fitness')
    bio = models.TextField(blank=True, default='')
    experience_years = models.PositiveIntegerField(default=1)
    certifications = models.TextField(blank=True, default='')
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    joined_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['user__first_name', 'user__last_name']
        verbose_name = 'Trainer'
        verbose_name_plural = 'Trainers'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.specialization})"

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
    def assigned_members_count(self):
        return self.assigned_members.filter(status='ACTIVE').count()
