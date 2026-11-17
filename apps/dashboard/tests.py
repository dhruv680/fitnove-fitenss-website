from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, GymOrganization, GymBranch
from apps.memberships.models import MembershipPlan
from apps.crm.models import Lead
from apps.notifications.models import Notification

class NavbarNavigationTests(TestCase):
    def setUp(self):
        self.org = GymOrganization.objects.create(name="FitNova HQ", currency="$", phone="+1 555-0100", email="info@fitnova.com")
        self.branch = GymBranch.objects.create(organization=self.org, name="Downtown Branch", address="100 Fitness Blvd", city="Metro")
        self.admin = User.objects.create_user(
            username="admin_nav",
            email="admin_nav@fitnova.com",
            password="pass",
            role=User.Role.GYM_ADMIN,
            organization=self.org,
            branch=self.branch
        )
        self.plan = MembershipPlan.objects.create(
            organization=self.org,
            name="Platinum All-Access",
            price=120.00,
            duration_days=30,
            is_active=True
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_navbar_contains_all_five_navigation_links(self):
        url = reverse('dashboard:index')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        # Check all 5 navigation links are in the rendered navbar
        self.assertIn(reverse('dashboard:index'), content)
        self.assertIn(reverse('dashboard:about'), content)
        self.assertIn(reverse('dashboard:services'), content)
        self.assertIn(reverse('dashboard:contact'), content)
        self.assertIn(reverse('dashboard:apply'), content)

        # Check visible link texts
        self.assertIn("Home", content)
        self.assertIn("About Us", content)
        self.assertIn("Services", content)
        self.assertIn("Contact Us", content)
        self.assertIn("Apply Now", content)

    def test_about_us_page_renders_mission_vision_facilities(self):
        url = reverse('dashboard:about')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        self.assertIn("About Us", content)
        self.assertIn("Our Mission", content)
        self.assertIn("Our Vision", content)
        self.assertIn("Olympic Free-Weight Zone", content)
        self.assertIn("Cardio Theater & HIIT Lab", content)

    def test_services_page_renders_services_and_plans(self):
        url = reverse('dashboard:services')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        self.assertIn("Services & Membership Plans", content)
        self.assertIn("1-on-1 Personal Coaching", content)
        self.assertIn("Biometric Smart Pass System", content)
        # Check plan from database
        self.assertIn("Platinum All-Access", content)
        self.assertIn("120.00", content)

    def test_contact_us_get_and_post_submission(self):
        url = reverse('dashboard:contact')
        # GET
        resp_get = self.client.get(url)
        self.assertEqual(resp_get.status_code, 200)
        content_get = resp_get.content.decode('utf-8')
        self.assertIn("Send Us a Direct Message", content_get)

        # POST valid contact inquiry
        post_data = {
            'name': 'Marcus Brody',
            'email': 'brody@example.com',
            'phone': '+1 555-0888',
            'subject': 'Personal Coaching Consultation',
            'message': 'Interested in 1-on-1 coaching for marathon training.'
        }
        resp_post = self.client.post(url, post_data)
        self.assertEqual(resp_post.status_code, 302)

        # Verify lead created in DB
        lead = Lead.objects.filter(email='brody@example.com').first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.full_name, 'Marcus Brody')
        self.assertEqual(lead.source, Lead.Source.WEBSITE)
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertIn('marathon training', lead.notes)

        # Verify notification created
        notif = Notification.objects.filter(recipient=self.admin).first()
        self.assertIsNotNone(notif)
        self.assertIn('Marcus Brody', notif.title)

    def test_apply_now_get_and_post_submission(self):
        url = reverse('dashboard:apply')
        # GET with preselected plan
        resp_get = self.client.get(url + f'?plan={self.plan.id}')
        self.assertEqual(resp_get.status_code, 200)
        content_get = resp_get.content.decode('utf-8')
        self.assertIn("FitNova Athlete Membership Application", content_get)
        self.assertIn("Platinum All-Access", content_get)

        # POST valid application
        post_data = {
            'full_name': 'Natasha Romanoff',
            'email': 'natasha@example.com',
            'phone': '+1 555-0777',
            'gender': 'FEMALE',
            'date_of_birth': '1995-05-15',
            'plan_id': self.plan.id,
            'fitness_goals': 'Strength & Power Lifting',
            'emergency_name': 'Clint Barton',
            'emergency_phone': '+1 555-0778',
            'medical_history': 'No pre-existing conditions.'
        }
        resp_post = self.client.post(url, post_data)
        self.assertEqual(resp_post.status_code, 200)
        content_post = resp_post.content.decode('utf-8')
        self.assertIn("APPLICATION RECEIVED", content_post)
        self.assertIn("Welcome to the FitNova Community, Natasha Romanoff!", content_post)
        self.assertIn("Platinum All-Access", content_post)

        # Verify lead created in DB
        lead = Lead.objects.filter(email='natasha@example.com').first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.full_name, 'Natasha Romanoff')
        self.assertEqual(lead.source, Lead.Source.WEBSITE)
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertIn('Clint Barton', lead.notes)
