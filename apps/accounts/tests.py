from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, GymOrganization, GymBranch

class RoleBasedAccessControlTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.org = GymOrganization.objects.create(name='Test Gym', slug='test-gym', phone='1234567890')
        self.branch = GymBranch.objects.create(organization=self.org, name='Main Branch', code='TB-01', phone='1234567890')
        self.admin = User.objects.create_user(username='admin_user', password='password123', organization=self.org, branch=self.branch, role=User.Role.GYM_ADMIN)
        self.member = User.objects.create_user(username='member_user', password='password123', organization=self.org, branch=self.branch, role=User.Role.MEMBER)

    def test_unauthenticated_redirect_to_login(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_admin_can_access_members(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('members:member_list'))
        self.assertEqual(response.status_code, 200)

    def test_member_blocked_from_admin_pages(self):
        self.client.login(username='member_user', password='password123')
        # Member trying to access staff/admin page
        response = self.client.get(reverse('members:member_list'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:index'))

