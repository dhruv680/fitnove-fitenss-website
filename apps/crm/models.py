from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.accounts.models import GymOrganization, GymBranch

class Lead(models.Model):
    class Source(models.TextChoices):
        WALK_IN = 'WALK_IN', 'Walk-in / In-Person'
        WEBSITE = 'WEBSITE', 'Website Inquiry'
        INSTAGRAM = 'INSTAGRAM', 'Instagram'
        FACEBOOK = 'FACEBOOK', 'Facebook'
        REFERRAL = 'REFERRAL', 'Member Referral'
        GOOGLE = 'GOOGLE', 'Google Search / Maps'

    class Status(models.TextChoices):
        NEW = 'NEW', 'New Inquiry'
        CONTACTED = 'CONTACTED', 'Contacted / Called'
        TRIAL_SCHEDULED = 'TRIAL_SCHEDULED', 'Free Trial Scheduled'
        TRIAL_ATTENDED = 'TRIAL_ATTENDED', 'Trial Attended'
        CONVERTED = 'CONVERTED', 'Converted to Member'
        LOST = 'LOST', 'Lost / Not Interested'

    organization = models.ForeignKey(
        GymOrganization,
        on_delete=models.CASCADE,
        related_name='leads'
    )
    branch = models.ForeignKey(
        GymBranch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads'
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=25)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.WALK_IN)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    interest = models.CharField(max_length=100, default='General Gym Membership')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads'
    )
    trial_date = models.DateField(null=True, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'CRM Lead'
        verbose_name_plural = 'CRM Leads'

    def __str__(self):
        return f"{self.full_name} ({self.get_status_display()})"
