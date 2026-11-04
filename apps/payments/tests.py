from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User, GymOrganization, GymBranch
from apps.members.models import Member
from apps.memberships.models import MembershipPlan
from apps.payments.models import Payment, Invoice
from apps.payments.services import PaymentService

class PaymentServiceTestCase(TestCase):
    def setUp(self):
        self.org = GymOrganization.objects.create(name='Test Gym', slug='test-gym', phone='1234567890')
        self.branch = GymBranch.objects.create(organization=self.org, name='Main Branch', code='TB-01', phone='1234567890')
        self.user = User.objects.create_user(username='testmember2', password='password123', organization=self.org, branch=self.branch, role=User.Role.MEMBER)
        self.member = Member.objects.create(
            user=self.user,
            organization=self.org,
            branch=self.branch,
            member_id='FN-TEST-002',
            status=Member.Status.PENDING
        )
        self.plan = MembershipPlan.objects.create(organization=self.org, name='VIP Annual', slug='vip-annual', price=500.00, duration_days=365)

    def test_payment_and_invoice_creation(self):
        payment, invoice = PaymentService.record_membership_payment(
            member=self.member,
            plan=self.plan,
            amount=Decimal('500.00'),
            payment_method=Payment.Method.UPI
        )
        self.assertIsNotNone(payment.id)
        self.assertIsNotNone(invoice.id)
        self.assertEqual(payment.total_amount, Decimal('500.00'))
        self.assertEqual(invoice.total, Decimal('500.00'))
        self.assertEqual(self.member.status, Member.Status.ACTIVE)
        self.assertTrue(invoice.invoice_number.startswith('INV-'))

