from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User, GymOrganization, GymBranch
from apps.members.models import Member
from apps.trainers.models import Trainer
from apps.attendance.models import Attendance
from apps.facilities.models import (
    GymEquipment, CardioProgram, SprintTurfSession, TurfBooking,
    RecoveryFacility, RecoveryBooking, FuelBarItem, FuelBarOrder
)


class FacilitiesTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Organization & Branch
        self.org = GymOrganization.objects.create(
            name="FitNova Elite",
            slug="fitnova-elite",
            phone="555-1234",
            email="contact@fitnova.com"
        )
        self.branch = GymBranch.objects.create(
            organization=self.org,
            name="Downtown",
            code="FN-DT-01",
            address="123 Gym St",
            city="Metropolis",
            phone="555-0001"
        )

        # Admin user
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='Password@123',
            role=User.Role.SUPER_ADMIN,
            organization=self.org,
            branch=self.branch
        )

        # Member user
        self.member_user = User.objects.create_user(
            username='member_test',
            email='member@test.com',
            password='Password@123',
            role=User.Role.MEMBER,
            organization=self.org,
            branch=self.branch
        )
        self.member = Member.objects.create(
            user=self.member_user,
            organization=self.org,
            branch=self.branch,
            member_id="FN-TEST-001",
            status=Member.Status.ACTIVE
        )

        # Trainer user
        self.trainer_user = User.objects.create_user(
            username='trainer_test',
            email='trainer@test.com',
            password='Password@123',
            role=User.Role.TRAINER,
            organization=self.org,
            branch=self.branch
        )
        self.trainer = Trainer.objects.create(
            user=self.trainer_user,
            organization=self.org,
            branch=self.branch,
            employee_id="TR-TEST-001",
            specialization="Strength & Conditioning"
        )

        # Seed test items
        self.barbell = GymEquipment.objects.create(
            name="Eleiko Competition Barbell",
            zone=GymEquipment.Zone.FREE_WEIGHTS,
            category="Barbells",
            brand="Eleiko",
            status=GymEquipment.Status.AVAILABLE
        )

        self.treadmill = GymEquipment.objects.create(
            name="Woodway Curve Deck",
            zone=GymEquipment.Zone.CARDIO_HIIT,
            category="Treadmills",
            brand="Woodway",
            status=GymEquipment.Status.AVAILABLE
        )

        self.turf_session = SprintTurfSession.objects.create(
            title="Sled Sprint Drills",
            trainer=self.trainer,
            capacity=15,
            schedule_info="Tue, Thu • 06:30 PM"
        )

        self.cryo = RecoveryFacility.objects.create(
            name="Cryo Chamber",
            facility_type=RecoveryFacility.FacilityType.CRYO,
            temperature="-110°C",
            duration_minutes=3,
            capacity_per_slot=2
        )

        self.smoothie = FuelBarItem.objects.create(
            name="Double Chocolate Whey Shake",
            category=FuelBarItem.Category.SMOOTHIE,
            price=Decimal("8.50"),
            protein_grams=40
        )

    def test_01_free_weights_page_and_status_toggle(self):
        self.client.login(username='admin_test', password='Password@123')
        res = self.client.get(reverse('facilities:free_weights'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Olympic Free-Weight Zone")
        self.assertContains(res, "Eleiko Competition Barbell")

        # Toggle status to IN_USE
        post_res = self.client.post(
            reverse('facilities:toggle_equipment_status', args=[self.barbell.id]),
            {'status': 'IN_USE'}
        )
        self.barbell.refresh_from_db()
        self.assertEqual(self.barbell.status, GymEquipment.Status.IN_USE)

    def test_02_cardio_hiit_page_and_add_program(self):
        self.client.login(username='admin_test', password='Password@123')
        res = self.client.get(reverse('facilities:cardio_hiit'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Cardio Theater & HIIT Lab")
        self.assertContains(res, "Woodway Curve Deck")

        # Add cardio program
        post_res = self.client.post(reverse('facilities:add_cardio_program'), {
            'title': 'Test MetCon 30',
            'duration_minutes': 30,
            'calories_burn': 400,
            'difficulty': 'Intermediate'
        })
        self.assertTrue(CardioProgram.objects.filter(title='Test MetCon 30').exists())

    def test_03_sprint_turf_page_and_member_booking(self):
        self.client.login(username='member_test', password='Password@123')
        res = self.client.get(reverse('facilities:sprint_turf'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Functional Sprint Turf")
        self.assertContains(res, "Sled Sprint Drills")

        # Member books spot
        book_res = self.client.post(reverse('facilities:book_turf_session', args=[self.turf_session.id]))
        self.assertTrue(TurfBooking.objects.filter(session=self.turf_session, member=self.member).exists())

    def test_04_biometric_access_page_and_security(self):
        self.client.login(username='member_test', password='Password@123')
        res = self.client.get(reverse('facilities:biometric_access'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Smart Biometric Access")
        self.assertContains(res, "Live Biometric Turnstile Terminal")

        # Test API rejects unverified face
        api_res = self.client.post(reverse('facilities:api_biometric_verify'), {'image': ''})
        self.assertEqual(api_res.status_code, 400)

    def test_05_recovery_spa_page_and_booking(self):
        self.client.login(username='member_test', password='Password@123')
        res = self.client.get(reverse('facilities:recovery_spa'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Recovery & Cryo Spa")
        self.assertContains(res, "Cryo Chamber")

        # Book recovery session
        book_res = self.client.post(reverse('facilities:book_recovery'), {
            'facility_id': self.cryo.id,
            'booking_date': timezone.now().strftime('%Y-%m-%d'),
            'time_slot': '10:00 AM - 10:30 AM',
            'notes': 'Post-squat cryo session'
        })
        self.assertTrue(RecoveryBooking.objects.filter(facility=self.cryo, member=self.member).exists())

    def test_06_fuel_bar_page_and_order(self):
        self.client.login(username='member_test', password='Password@123')
        res = self.client.get(reverse('facilities:fuel_bar'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Athlete Fuel Bar & Lounge")
        self.assertContains(res, "Double Chocolate Whey Shake")

        # Place Fuel Bar order
        order_res = self.client.post(reverse('facilities:create_fuel_order'), {
            'item_id': self.smoothie.id,
            'quantity': 2,
            'notes': 'Extra ice'
        })
        self.assertTrue(FuelBarOrder.objects.filter(member=self.member).exists())
        order = FuelBarOrder.objects.filter(member=self.member).first()
        self.assertEqual(order.total_price, Decimal('17.00'))

    def test_07_about_page_has_all_six_clickable_links(self):
        self.client.login(username='member_test', password='Password@123')
        res = self.client.get(reverse('dashboard:about'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, reverse('facilities:free_weights'))
        self.assertContains(res, reverse('facilities:cardio_hiit'))
        self.assertContains(res, reverse('facilities:sprint_turf'))
        self.assertContains(res, reverse('facilities:biometric_access'))
        self.assertContains(res, reverse('facilities:recovery_spa'))
        self.assertContains(res, reverse('facilities:fuel_bar'))
