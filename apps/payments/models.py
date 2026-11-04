import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.accounts.models import GymOrganization, GymBranch

class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = 'CASH', 'Cash'
        UPI = 'UPI', 'UPI / QR Payment'
        CREDIT_CARD = 'CREDIT_CARD', 'Credit Card'
        DEBIT_CARD = 'DEBIT_CARD', 'Debit Card'
        NET_BANKING = 'NET_BANKING', 'Net Banking'
        ONLINE = 'ONLINE', 'Online Gateway (Stripe/Razorpay)'

    class Status(models.TextChoices):
        COMPLETED = 'COMPLETED', 'Completed'
        PENDING = 'PENDING', 'Pending'
        REFUNDED = 'REFUNDED', 'Refunded'
        FAILED = 'FAILED', 'Failed'

    organization = models.ForeignKey(
        GymOrganization,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    branch = models.ForeignKey(
        GymBranch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branch_payments'
    )
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    membership = models.ForeignKey(
        'memberships.Membership',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.UPI
    )
    transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED
    )
    payment_date = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_payments'
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-payment_date']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f"{self.transaction_id} - {self.member.full_name} ({self.organization.currency}{self.total_amount})"


class Invoice(models.Model):
    class Status(models.TextChoices):
        PAID = 'PAID', 'Paid'
        UNPAID = 'UNPAID', 'Unpaid'
        OVERDUE = 'OVERDUE', 'Overdue'
        CANCELLED = 'CANCELLED', 'Cancelled'

    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='invoice'
    )
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField(default=timezone.now)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PAID
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issue_date', '-id']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f"Invoice #{self.invoice_number} ({self.payment.member.full_name})"


class Expense(models.Model):
    class Category(models.TextChoices):
        RENT = 'RENT', 'Rent & Lease'
        EQUIPMENT = 'EQUIPMENT', 'Gym Equipment & Maintenance'
        SALARIES = 'SALARIES', 'Staff & Trainer Salaries'
        UTILITIES = 'UTILITIES', 'Electricity & Water'
        MARKETING = 'MARKETING', 'Marketing & Ads'
        SUPPLEMENTS = 'SUPPLEMENTS', 'Supplements & Goods'
        CLEANING = 'CLEANING', 'Hygiene & Cleaning'
        OTHER = 'OTHER', 'Other Operating Expense'

    organization = models.ForeignKey(
        GymOrganization,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    branch = models.ForeignKey(
        GymBranch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)
    paid_to = models.CharField(max_length=150, blank=True, default='')
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_expenses'
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Gym Expense'
        verbose_name_plural = 'Gym Expenses'

    def __str__(self):
        return f"{self.title} - {self.organization.currency}{self.amount} ({self.get_category_display()})"

