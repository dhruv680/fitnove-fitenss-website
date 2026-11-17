import base64
import json
from io import BytesIO
from PIL import Image, ImageDraw
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, GymOrganization, GymBranch, UserFaceProfile

def generate_test_face_image_base64(color=(120, 100, 90)):
    img = Image.new('RGB', (160, 160), color=color)
    draw = ImageDraw.Draw(img)
    # Draw simple facial feature shapes
    draw.ellipse((35, 45, 65, 70), fill=(40, 30, 25))   # Left eye
    draw.ellipse((95, 45, 125, 70), fill=(40, 30, 25))  # Right eye
    draw.polygon([(80, 70), (70, 100), (90, 100)], fill=(70, 50, 45)) # Nose
    draw.rectangle((55, 115, 105, 130), fill=(180, 60, 60)) # Mouth
    buf = BytesIO()
    img.save(buf, format='JPEG')
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')


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
        response = self.client.get(reverse('members:member_list'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:index'))


class RegistrationAndFaceAuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.org = GymOrganization.objects.create(name='FitNova Elite', slug='fitnova-elite', phone='9876543210')
        self.branch = GymBranch.objects.create(organization=self.org, name='Downtown', code='FN-01', phone='9876543210')

    def test_registration_success(self):
        payload = {
            'full_name': 'Marcus Vance',
            'username': 'marcus_vance',
            'email': 'marcus@fitnova.com',
            'phone': '+1234567890',
            'gender': 'MALE',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'terms': 'on',
        }
        response = self.client.post(reverse('accounts:register'), data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:face_enroll'))

        # User is created
        user = User.objects.get(email='marcus@fitnova.com')
        self.assertEqual(user.username, 'marcus_vance')
        self.assertEqual(user.first_name, 'Marcus')
        self.assertEqual(user.last_name, 'Vance')
        self.assertEqual(user.gender, 'MALE')
        self.assertEqual(self.client.session.get('face_enroll_user_id'), user.id)

    def test_registration_duplicate_username_fails(self):
        User.objects.create_user(username='taken_user', email='first@fitnova.com', password='password123')
        payload = {
            'full_name': 'New Athlete',
            'username': 'taken_user',
            'email': 'second@fitnova.com',
            'phone': '1234567890',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'terms': 'on',
        }
        response = self.client.post(reverse('accounts:register'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'username is already taken')

    def test_registration_duplicate_email_fails(self):
        User.objects.create_user(username='existing', email='duplicate@fitnova.com', password='password123')
        payload = {
            'full_name': 'Another User',
            'email': 'duplicate@fitnova.com',
            'phone': '1234567890',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'terms': 'on',
        }
        response = self.client.post(reverse('accounts:register'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')

    def test_registration_mismatched_password_fails(self):
        payload = {
            'full_name': 'Test User',
            'email': 'test@fitnova.com',
            'phone': '1234567890',
            'password': 'PasswordOne1!',
            'confirm_password': 'PasswordTwo2!',
            'terms': 'on',
        }
        response = self.client.post(reverse('accounts:register'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match')

    def test_face_enrollment_api(self):
        user = User.objects.create_user(username='athlete1', email='athlete1@fitnova.com', password='password123')
        session = self.client.session
        session['face_enroll_user_id'] = user.id
        session.save()

        img_b64 = generate_test_face_image_base64()
        response = self.client.post(reverse('accounts:api_face_enroll'), data={'image': img_b64})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        user.refresh_from_db()
        self.assertTrue(user.has_face_enrolled)
        self.assertTrue(UserFaceProfile.objects.filter(user=user).exists())

    def test_login_flow_with_face_verification(self):
        user = User.objects.create_user(username='athlete2', email='athlete2@fitnova.com', password='secretpassword')
        img_b64 = generate_test_face_image_base64()

        # Enroll face first
        session = self.client.session
        session['face_enroll_user_id'] = user.id
        session.save()
        self.client.post(reverse('accounts:api_face_enroll'), data={'image': img_b64})

        # Submit username/password at login
        login_resp = self.client.post(reverse('accounts:login'), data={
            'username': 'athlete2@fitnova.com',
            'password': 'secretpassword'
        })
        self.assertEqual(login_resp.status_code, 302)
        self.assertEqual(login_resp.url, reverse('accounts:face_verify'))
        self.assertEqual(self.client.session.get('face_auth_pending_user_id'), user.id)

        # Middleware blocks accessing dashboard while face auth is pending
        dash_resp = self.client.get(reverse('dashboard:index'))
        self.assertEqual(dash_resp.status_code, 302)
        self.assertEqual(dash_resp.url, reverse('accounts:face_verify'))

        # Verify face with matching image
        verify_resp = self.client.post(reverse('accounts:api_face_verify'), data={'image': img_b64})
        self.assertEqual(verify_resp.status_code, 200)
        verify_data = verify_resp.json()
        self.assertTrue(verify_data['success'])

        # Now dashboard is accessible
        dash_resp_after = self.client.get(reverse('dashboard:index'))
        self.assertEqual(dash_resp_after.status_code, 200)

    def test_face_fallback_with_password(self):
        user = User.objects.create_user(username='athlete3', email='athlete3@fitnova.com', password='myfallbackpass')
        session = self.client.session
        session['face_auth_pending_user_id'] = user.id
        session.save()

        # Wrong password
        fail_resp = self.client.post(reverse('accounts:face_fallback'), data={'password': 'wrong'})
        self.assertEqual(fail_resp.status_code, 200)
        self.assertContains(fail_resp, 'Incorrect password')

        # Correct password
        ok_resp = self.client.post(reverse('accounts:face_fallback'), data={'password': 'myfallbackpass'})
        self.assertEqual(ok_resp.status_code, 302)
        self.assertEqual(ok_resp.url, reverse('dashboard:index'))
