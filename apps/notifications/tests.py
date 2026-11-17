from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, GymOrganization
from apps.notifications.models import Notification

class NotificationsModuleTests(TestCase):
    def setUp(self):
        self.org = GymOrganization.objects.create(name="FitNova HQ")
        self.user = User.objects.create_user(
            username="notif_tester",
            email="notif@fitnova.com",
            password="pass",
            role=User.Role.GYM_ADMIN,
            organization=self.org
        )
        self.n1 = Notification.objects.create(
            recipient=self.user,
            title="Membership Renewal Due",
            message="Your membership is expiring soon.",
            notification_type=Notification.NotificationType.EXPIRY,
            action_url="/payments/invoices/"
        )
        self.n2 = Notification.objects.create(
            recipient=self.user,
            title="Welcome to FitNova",
            message="Glad to have you with us.",
            notification_type=Notification.NotificationType.INFO
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_notification_filters_and_mark_read(self):
        url = reverse('notifications:list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['unread_count'], 2)

        # Mark single as read without navigate
        mark_url = reverse('notifications:mark_read', kwargs={'pk': self.n1.pk})
        resp_mark = self.client.get(mark_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp_mark.status_code, 200)
        json_data = resp_mark.json()
        self.assertTrue(json_data['success'])
        self.assertEqual(json_data['unread_count'], 1)

        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

        # Mark all read
        mark_all_url = reverse('notifications:mark_all_read')
        resp_all = self.client.get(mark_all_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp_all.status_code, 200)
        self.assertEqual(self.user.notifications.filter(is_read=False).count(), 0)

    def test_view_details_navigates_to_action_url(self):
        mark_nav_url = reverse('notifications:mark_read', kwargs={'pk': self.n1.pk}) + '?navigate=1'
        resp = self.client.get(mark_nav_url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.n1.action_url)
