import uuid
import datetime
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Payment, Invoice, Expense
from apps.members.models import Member
from apps.memberships.models import Membership, MembershipPlan
from apps.memberships.services import MembershipService

class PaymentService:
    @staticmethod
    def get_scoped_payments(user):
        if user.is_super_admin:
            return Payment.objects.select_related('member__user', 'membership__plan', 'organization').all()
        return Payment.objects.select_related('member__user', 'membership__plan', 'organization').filter(organization=user.organization)

    @staticmethod
    def get_scoped_invoices(user):
        if user.is_super_admin:
            return Invoice.objects.select_related('payment__member__user', 'payment__organization', 'payment__membership__plan').all()
        return Invoice.objects.select_related('payment__member__user', 'payment__organization', 'payment__membership__plan').filter(payment__organization=user.organization)

    @staticmethod
    def get_scoped_expenses(user):
        if user.is_super_admin:
            return Expense.objects.select_related('organization', 'branch', 'recorded_by').all()
        return Expense.objects.select_related('organization', 'branch', 'recorded_by').filter(organization=user.organization)

    @staticmethod
    @transaction.atomic
    def record_membership_payment(member, plan, amount, payment_method, recorded_by=None, transaction_id=None, notes=''):
        today = timezone.now()
        org = member.organization
        branch = member.branch

        if not transaction_id:
            transaction_id = f"TXN-{today.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        # Prevent duplicate transaction_id
        if Payment.objects.filter(transaction_id=transaction_id).exists():
            raise ValueError("A transaction with this ID already exists.")

        amount_dec = Decimal(str(amount))
        # Activate / Renew membership
        membership = MembershipService.assign_membership(member=member, plan=plan, notes=f"Paid via {payment_method}")

        payment = Payment.objects.create(
            organization=org,
            branch=branch,
            member=member,
            membership=membership,
            amount=amount_dec,
            tax_amount=Decimal('0.00'),
            total_amount=amount_dec,
            payment_method=payment_method,
            transaction_id=transaction_id,
            status=Payment.Status.COMPLETED,
            payment_date=today,
            recorded_by=recorded_by,
            notes=notes
        )

        # Generate Invoice
        year = today.year
        inv_count = Invoice.objects.filter(payment__organization=org).count() + 1
        invoice_number = f"INV-{year}-{inv_count:05d}"

        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            payment=payment,
            issue_date=today.date(),
            due_date=today.date(),
            subtotal=amount_dec,
            tax=Decimal('0.00'),
            total=amount_dec,
            status=Invoice.Status.PAID
        )

        return payment, invoice

