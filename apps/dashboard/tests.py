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

    def test_social_media_section_in_footer(self):
        url = reverse('dashboard:index')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        # Check all 4 official brand social media buttons are rendered
        self.assertIn("fn-social-btn instagram", content)
        self.assertIn("fn-social-btn linkedin", content)
        self.assertIn("fn-social-btn whatsapp", content)
        self.assertIn("fn-social-btn twitter", content)

        # Check tooltips
        self.assertIn("Instagram", content)
        self.assertIn("LinkedIn", content)
        self.assertIn("WhatsApp", content)
        self.assertIn("Twitter / X", content)

        # Check WhatsApp link uses phone from organization
        self.assertIn("https://wa.me/15550100", content)

    def test_social_media_section_in_contact_page(self):
        url = reverse('dashboard:contact')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')

        self.assertIn("Connect Across Social Channels", content)
        self.assertIn("fn-social-btn instagram", content)
        self.assertIn("fn-social-btn whatsapp", content)


class BranchManagementCRUDTests(TestCase):
    def setUp(self):
        self.org = GymOrganization.objects.create(
            name="FitNova HQ",
            slug="fitnova-hq",
            currency="$",
            phone="+1 555-0100",
            email="info@fitnova.com"
        )
        self.branch1 = GymBranch.objects.create(
            organization=self.org,
            name="Downtown Center",
            code="FN-DT-01",
            address="100 Main St",
            city="Metropolis",
            state="NY",
            zip_code="10001",
            phone="+1 555-1111",
            email="dt@fitnova.com",
            manager_name="Alex Cross",
            is_main_branch=True,
            is_active=True
        )
        self.admin = User.objects.create_user(
            username="branch_admin",
            email="admin@fitnova.com",
            password="pass",
            role=User.Role.GYM_ADMIN,
            organization=self.org,
            branch=self.branch1
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_settings_page_lists_all_branches(self):
        url = reverse('dashboard:settings')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Downtown Center", resp.content.decode('utf-8'))
        self.assertIn("FN-DT-01", resp.content.decode('utf-8'))
        self.assertIn("accounts_gymbranch", resp.content.decode('utf-8'))

    def test_branch_create_view_inserts_row(self):
        url = reverse('dashboard:branch_create')
        data = {
            'name': 'Uptown Performance Hub',
            'code': 'FN-UP-02',
            'address': '250 Park Avenue',
            'city': 'Metropolis',
            'state': 'NY',
            'zip_code': '10022',
            'phone': '+1 555-2222',
            'email': 'uptown@fitnova.com',
            'manager_name': 'Eleanor Vance',
            'is_main_branch': 'off',
            'is_active': 'on'
        }
        resp = self.client.post(url, data, follow=True)
        self.assertEqual(resp.status_code, 200)
        
        # Verify row exists in DB
        branch = GymBranch.objects.filter(code='FN-UP-02').first()
        self.assertIsNotNone(branch)
        self.assertEqual(branch.name, 'Uptown Performance Hub')
        self.assertEqual(branch.city, 'Metropolis')
        self.assertEqual(branch.organization, self.org)
        self.assertTrue(branch.is_active)
        self.assertFalse(branch.is_main_branch)

    def test_branch_update_view_modifies_row(self):
        url = reverse('dashboard:branch_update', args=[self.branch1.id])
        data = {
            'name': 'Downtown Flagship Center',
            'code': 'FN-DT-01',
            'address': '100 Main St Suite 500',
            'city': 'Metropolis',
            'state': 'NY',
            'zip_code': '10001',
            'phone': '+1 555-9999',
            'email': 'dt_flagship@fitnova.com',
            'manager_name': 'Alexander Cross',
            'is_main_branch': 'on',
            'is_active': 'on'
        }
        resp = self.client.post(url, data, follow=True)
        self.assertEqual(resp.status_code, 200)

        self.branch1.refresh_from_db()
        self.assertEqual(self.branch1.name, 'Downtown Flagship Center')
        self.assertEqual(self.branch1.phone, '+1 555-9999')
        self.assertEqual(self.branch1.address, '100 Main St Suite 500')

    def test_branch_toggle_status(self):
        url = reverse('dashboard:branch_toggle_status', args=[self.branch1.id])
        resp = self.client.post(url, follow=True)
        self.assertEqual(resp.status_code, 200)

        self.branch1.refresh_from_db()
        self.assertFalse(self.branch1.is_active)

    def test_branch_delete_with_fallback(self):
        # Create second branch so first can be deleted
        branch2 = GymBranch.objects.create(
            organization=self.org,
            name="Northside Center",
            code="FN-NO-03",
            address="400 North Blvd",
            city="Metropolis",
            is_active=True
        )
        url = reverse('dashboard:branch_delete', args=[self.branch1.id])
        resp = self.client.post(url, follow=True)
        self.assertEqual(resp.status_code, 200)

        self.assertFalse(GymBranch.objects.filter(id=self.branch1.id).exists())
        branch2.refresh_from_db()
        self.assertTrue(branch2.is_main_branch)


