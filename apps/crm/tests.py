from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, GymOrganization, GymBranch
from apps.crm.models import Lead

class CRMModuleTests(TestCase):
    def setUp(self):
        self.org = GymOrganization.objects.create(name="FitNova HQ", currency="$")
        self.branch = GymBranch.objects.create(organization=self.org, name="Downtown")
        self.admin = User.objects.create_user(
            username="admin_crm_test",
            email="admin_crm@fitnova.com",
            password="pass",
            role=User.Role.GYM_ADMIN,
            organization=self.org,
            branch=self.branch
        )
        self.lead1 = Lead.objects.create(
            organization=self.org,
            branch=self.branch,
            full_name="Sarah Connor",
            phone="+1 555-0101",
            email="sarah@example.com",
            status=Lead.Status.NEW
        )
        self.lead2 = Lead.objects.create(
            organization=self.org,
            branch=self.branch,
            full_name="John Matrix",
            phone="+1 555-0102",
            email="matrix@example.com",
            status=Lead.Status.CONTACTED
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_pipeline_counts_preserved_when_filtering_stage(self):
        # Filtering by status=NEW should NOT set counts for CONTACTED to 0
        url = reverse('crm:lead_list') + '?status=NEW'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        counts = resp.context['counts']
        self.assertEqual(counts['total'], 2)
        self.assertEqual(counts['new'], 1)
        self.assertEqual(counts['contacted'], 1)

    def test_lead_capture_and_status_update(self):
        create_url = reverse('crm:lead_create')
        data = {
            'full_name': 'Ellen Ripley',
            'phone': '+1 555-0103',
            'email': 'ripley@example.com',
            'interest': 'VIP Annual Plan'
        }
        resp = self.client.post(create_url, data)
        self.assertEqual(resp.status_code, 302)

        lead = Lead.objects.filter(email='ripley@example.com').first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.status, Lead.Status.NEW)

        # Status update via AJAX
        status_url = reverse('crm:lead_update_status', kwargs={'pk': lead.pk})
        resp_status = self.client.post(
            status_url,
            {'status': Lead.Status.TRIAL_SCHEDULED, 'note': 'Trial booked for Saturday'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp_status.status_code, 200)
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.TRIAL_SCHEDULED)
