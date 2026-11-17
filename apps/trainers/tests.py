from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, GymOrganization, GymBranch
from apps.trainers.models import Trainer

class TrainersModuleTests(TestCase):
    def setUp(self):
        self.org = GymOrganization.objects.create(name="FitNova HQ", currency="$")
        self.branch = GymBranch.objects.create(organization=self.org, name="Downtown")
        self.admin = User.objects.create_user(
            username="admin_trainer_test",
            email="admin_trn@fitnova.com",
            password="pass",
            role=User.Role.GYM_ADMIN,
            organization=self.org,
            branch=self.branch
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_trainer_create_and_edit(self):
        create_url = reverse('trainers:trainer_create')
        post_data = {
            'first_name': 'Marcus',
            'last_name': 'Vance',
            'email': 'marcus.vance@fitnova.com',
            'phone': '+1 555-0199',
            'specialization': 'CrossFit & Olympic Lifting',
            'experience_years': '6',
            'hourly_rate': '75.00',
            'rating': '4.9',
            'bio': 'Elite conditioning coach.',
            'certifications': 'CSCS, USAW Level 2'
        }
        resp = self.client.post(create_url, post_data)
        self.assertEqual(resp.status_code, 302)

        trainer = Trainer.objects.filter(user__email='marcus.vance@fitnova.com').first()
        self.assertIsNotNone(trainer)
        self.assertEqual(trainer.full_name, 'Marcus Vance')
        self.assertEqual(trainer.specialization, 'CrossFit & Olympic Lifting')
        self.assertEqual(trainer.experience_years, 6)
        self.assertEqual(float(trainer.hourly_rate), 75.00)
        self.assertEqual(float(trainer.rating), 4.9)

        # Test Trainer Edit
        edit_url = reverse('trainers:trainer_edit', kwargs={'pk': trainer.pk})
        edit_data = {
            'first_name': 'Marcus',
            'last_name': 'Vance',
            'phone': '+1 555-0999',
            'specialization': 'Strength & Conditioning',
            'experience_years': '7',
            'hourly_rate': '85.00',
            'rating': '5.0',
            'status': 'ACTIVE',
            'bio': 'Head Coach.',
            'certifications': 'CSCS'
        }
        resp_edit = self.client.post(edit_url, edit_data)
        self.assertEqual(resp_edit.status_code, 302)

        trainer.refresh_from_db()
        self.assertEqual(trainer.experience_years, 7)
        self.assertEqual(float(trainer.hourly_rate), 85.00)
        self.assertEqual(float(trainer.rating), 5.0)
        self.assertEqual(trainer.specialization, 'Strength & Conditioning')
