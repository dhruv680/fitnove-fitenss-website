from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User, GymOrganization, GymBranch
from apps.members.models import Member
from apps.memberships.models import MembershipPlan, Membership
from apps.attendance.models import Attendance
from apps.attendance.services import AttendanceService

class AttendanceServiceTestCase(TestCase):
    def setUp(self):
        self.org = GymOrganization.objects.create(name='Test Gym', slug='test-gym', phone='1234567890')
        self.branch = GymBranch.objects.create(organization=self.org, name='Main Branch', code='TB-01', phone='1234567890')
        self.user = User.objects.create_user(username='testmember', password='password123', organization=self.org, branch=self.branch, role=User.Role.MEMBER)
        self.member = Member.objects.create(
            user=self.user,
            organization=self.org,
            branch=self.branch,
            member_id='FN-TEST-001',
            status=Member.Status.ACTIVE
        )
        self.plan = MembershipPlan.objects.create(organization=self.org, name='Gold Plan', slug='gold', price=100.00, duration_days=30)
        self.membership = Membership.objects.create(
            member=self.member,
            plan=self.plan,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            status=Membership.Status.ACTIVE
        )

    def test_check_in_success(self):
        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"
        success, msg, att, action = AttendanceService.process_check_in(qr_payload)
        self.assertTrue(success)
        self.assertEqual(action, 'CHECK_IN')
        self.assertEqual(att.status, Attendance.Status.PRESENT)

    def test_check_out_success(self):
        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"
        # First scan = Check in
        AttendanceService.process_check_in(qr_payload)
        # Second scan = Check out
        success, msg, att, action = AttendanceService.process_check_in(qr_payload)
        self.assertTrue(success)
        self.assertEqual(action, 'CHECK_OUT')
        self.assertEqual(att.status, Attendance.Status.CHECKED_OUT)
        self.assertIsNotNone(att.check_out_time)

    def test_duplicate_prevention(self):
        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"
        # 1st scan = check in
        AttendanceService.process_check_in(qr_payload)
        # 2nd scan = check out
        AttendanceService.process_check_in(qr_payload)
        # 3rd scan on same day = duplicate blocked!
        success, msg, att, action = AttendanceService.process_check_in(qr_payload)
        self.assertFalse(success)
        self.assertEqual(action, 'DUPLICATE')
        self.assertIn('already completed attendance today', msg)

