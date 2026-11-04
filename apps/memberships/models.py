from django.db import models
from django.utils import timezone
from apps.accounts.models import GymOrganization

class MembershipPlan(models.Model):
    class DurationType(models.TextChoices):
        MONTHLY = 'MONTHLY', 'Monthly (30 Days)'
        QUARTERLY = 'QUARTERLY', 'Quarterly (90 Days)'
        HALF_YEARLY = 'HALF_YEARLY', 'Half Yearly (180 Days)'
        YEARLY = 'YEARLY', 'Yearly (365 Days)'
        CUSTOM = 'CUSTOM', 'Custom Duration'

    organization = models.ForeignKey(
        GymOrganization,
        on_delete=models.CASCADE,
        related_name='plans'
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180)
    duration_type = models.CharField(
        max_length=20,
        choices=DurationType.choices,
        default=DurationType.MONTHLY
    )
    duration_days = models.PositiveIntegerField(default=30)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    signup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    features = models.TextField(help_text="Separate features by new line", default="Access to gym equipment\nLocker facility\nGeneral trainer support")
    has_trainer_included = models.BooleanField(default=False)
    has_locker_included = models.BooleanField(default=False)
    has_classes_included = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price']
        unique_together = ('organization', 'slug')
        verbose_name = 'Membership Plan'
        verbose_name_plural = 'Membership Plans'

    def __str__(self):
        return f"{self.name} - {self.organization.currency}{self.price} ({self.get_duration_type_display()})"

    @property
    def feature_list(self):
        return [f.strip() for f in self.features.split('\n') if f.strip()]


class Membership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        EXPIRED = 'EXPIRED', 'Expired'
        PENDING = 'PENDING', 'Pending Payment'
        CANCELLED = 'CANCELLED', 'Cancelled'

    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    plan = models.ForeignKey(
        MembershipPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )
    auto_renew = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Member Subscription'
        verbose_name_plural = 'Member Subscriptions'

    def __str__(self):
        return f"{self.member.full_name} - {self.plan.name} ({self.status})"

    @property
    def is_currently_active(self):
        today = timezone.now().date()
        return self.status == self.Status.ACTIVE and self.start_date <= today <= self.end_date

    @property
    def days_remaining(self):
        today = timezone.now().date()
        if self.end_date < today:
            return 0
        return (self.end_date - today).days
