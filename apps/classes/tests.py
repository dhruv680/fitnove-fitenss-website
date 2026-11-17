import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User, GymOrganization, GymBranch
from apps.members.models import Member
from apps.memberships.models import Membership, MembershipPlan
from apps.trainers.models import Trainer
from apps.classes.models import FitnessClass, ClassBooking

class ClassesModuleTests(TestCase):
    def setUp(self):
        self.org = GymOrganization.objects.create(name="FitNova HQ", currency="$")
        self.branch = GymBranch.objects.create(organization=self.org, name="Downtown")
        self.admin = User.objects.create_user(
            username="admin_test",
            email="admin@fitnova.com",
            password="pass",
            role=User.Role.GYM_ADMIN,
            organization=self.org,
            branch=self.branch
        )
        self.trainer_user = User.objects.create_user(
            username="trainer_test",
            email="trainer@fitnova.com",
            password="pass",
            role=User.Role.TRAINER,
            organization=self.org,
            branch=self.branch
        )
        self.trainer = Trainer.objects.create(
            user=self.trainer_user,
            organization=self.org,
            branch=self.branch,
            employee_id="TRN-9999",
            specialization="HIIT"
        )
        self.member_user = User.objects.create_user(
            username="member_test",
            email="member@fitnova.com",
            password="pass",
            role=User.Role.MEMBER,
            organization=self.org,
            branch=self.branch
        )
        self.member = Member.objects.create(
            user=self.member_user,
            organization=self.org,
            branch=self.branch,
            member_id="FN-9999",
            status=Member.Status.ACTIVE
        )
        self.plan = MembershipPlan.objects.create(
            organization=self.org,
            name="Gold Plan",
            price=99.00,
            duration_days=30
        )
        today = timezone.now().date()
        Membership.objects.create(
            member=self.member,
            plan=self.plan,
            start_date=today,
            end_date=today + datetime.timedelta(days=30),
            status=Membership.Status.ACTIVE
        )
        self.fitness_class = FitnessClass.objects.create(
            organization=self.org,
            branch=self.branch,
            name="Power Pilates",
            trainer=self.trainer,
            capacity=2,
            schedule_time=datetime.time(9, 0),
            duration_minutes=45,
            days_of_week="Mon, Wed",
            description="Intense core strengthening session."
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_class_list_renders_without_raw_template_variables(self):
        url = reverse('classes:class_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        # Check raw unrendered template tags do NOT exist
        self.assertNotIn("{{ card.obj.duration_minutes }}", content)
        self.assertNotIn("{{ card.obj.description", content)
        # Check actual values are rendered
        self.assertIn("Power Pilates", content)
        self.assertIn("45 mins", content)
        self.assertIn("Intense core strengthening session.", content)

    def test_class_booking_success_and_duplicate_prevention(self):
        url = reverse('classes:book_class', kwargs={'pk': self.fitness_class.pk})
        # First booking succeeds
        resp1 = self.client.post(url, {'member_id': self.member.id})
        self.assertEqual(resp1.status_code, 302)
        self.assertEqual(self.fitness_class.active_bookings_count(), 1)
        self.assertEqual(self.fitness_class.available_slots(), 1)

        # Duplicate booking on same day
        resp2 = self.client.post(url, {'member_id': self.member.id})
        self.assertEqual(resp2.status_code, 302)
        self.assertEqual(self.fitness_class.active_bookings_count(), 1)

    def test_class_capacity_limit(self):
        # Create second member
        m2_user = User.objects.create_user(username="m2", email="m2@fitnova.com", password="pass", role=User.Role.MEMBER, organization=self.org)
        m2 = Member.objects.create(user=m2_user, organization=self.org, member_id="FN-9998", status=Member.Status.ACTIVE)
        Membership.objects.create(member=m2, plan=self.plan, start_date=timezone.now().date(), end_date=timezone.now().date() + datetime.timedelta(days=30), status=Membership.Status.ACTIVE)

        # Create third member
        m3_user = User.objects.create_user(username="m3", email="m3@fitnova.com", password="pass", role=User.Role.MEMBER, organization=self.org)
        m3 = Member.objects.create(user=m3_user, organization=self.org, member_id="FN-9997", status=Member.Status.ACTIVE)
        Membership.objects.create(member=m3, plan=self.plan, start_date=timezone.now().date(), end_date=timezone.now().date() + datetime.timedelta(days=30), status=Membership.Status.ACTIVE)

        url = reverse('classes:book_class', kwargs={'pk': self.fitness_class.pk})
        self.client.post(url, {'member_id': self.member.id})
        self.client.post(url, {'member_id': m2.id})
        self.assertEqual(self.fitness_class.available_slots(), 0)

        # Third booking attempt when full capacity
        resp3 = self.client.post(url, {'member_id': m3.id})
        self.assertEqual(resp3.status_code, 302)
        # Count remains 2
        self.assertEqual(self.fitness_class.active_bookings_count(), 2)
