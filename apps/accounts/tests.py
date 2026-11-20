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
    # Draw standard facial feature shapes
    draw.ellipse((35, 45, 65, 70), fill=(40, 30, 25))   # Left eye
    draw.ellipse((95, 45, 125, 70), fill=(40, 30, 25))  # Right eye
    draw.polygon([(80, 70), (70, 100), (90, 100)], fill=(70, 50, 45)) # Nose
    draw.rectangle((55, 115, 105, 130), fill=(180, 60, 60)) # Mouth
    buf = BytesIO()
    img.save(buf, format='JPEG')
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')

def generate_different_face_image_base64():
    img = Image.new('RGB', (160, 160), color=(140, 180, 200))
    draw = ImageDraw.Draw(img)
    # Distinct facial geometry (different positioning and contours)
    draw.rectangle((50, 20, 110, 60), fill=(20, 40, 80))
    draw.ellipse((40, 75, 60, 95), fill=(10, 10, 10))
    draw.ellipse((100, 75, 120, 95), fill=(10, 10, 10))
    draw.line([(80, 80), (80, 130)], fill=(30, 30, 30), width=4)
    draw.polygon([(40, 135), (80, 155), (120, 135)], fill=(120, 40, 40))
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

    def test_unauthenticated_root_redirects_to_login(self):
        # Homepage '/' must automatically redirect unauthenticated visitors to Login Page
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:login'))

    def test_unauthenticated_protected_page_redirects_to_login(self):
        # Internal role-protected page redirects to login
        response = self.client.get(reverse('members:member_list'))
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

    def test_login_page_renders_cleanly_without_demo_buttons(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Demo Quick Sign-In')
        self.assertNotContains(response, 'fillLogin')
        self.assertContains(response, 'Create New Account')
        self.assertContains(response, reverse('accounts:register'))

    def test_registration_page_has_sign_in_link(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In')
        self.assertContains(response, reverse('accounts:login'))


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
            'role': 'MEMBER',
            'gender': 'MALE',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'terms': 'on',
        }
        response = self.client.post(reverse('accounts:register'), data=payload)
        self.assertEqual(response.status_code, 302)
        # Directly opens Face Detection after Registration
        self.assertEqual(response.url, reverse('accounts:face_enroll'))

        # User is created
        user = User.objects.get(email='marcus@fitnova.com')
        self.assertEqual(user.username, 'marcus_vance')
        self.assertEqual(user.first_name, 'Marcus')
        self.assertEqual(user.last_name, 'Vance')
        self.assertEqual(user.role, 'MEMBER')
        self.assertEqual(user.gender, 'MALE')

        # Direct face detection & enrollment redirects user to login page with registered flag
        img_b64 = generate_test_face_image_base64()
        enroll_resp = self.client.post(reverse('accounts:api_face_enroll'), data={'image': img_b64})
        self.assertEqual(enroll_resp.status_code, 200)
        self.assertEqual(enroll_resp.json()['redirect_url'], reverse('accounts:login') + '?registered=1')

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

        # Ensure client is logged out before testing new login flow
        self.client.logout()

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

    def test_direct_face_login_api_success(self):
        # Create user and enroll face
        user = User.objects.create_user(username='direct_face_user', email='direct@fitnova.com', password='secretpassword')
        img_b64 = generate_test_face_image_base64()

        session = self.client.session
        session['face_enroll_user_id'] = user.id
        session.save()
        self.client.post(reverse('accounts:api_face_enroll'), data={'image': img_b64})
        self.client.logout()

        # Direct Face Auth API Call without username/password
        response = self.client.post(reverse('accounts:api_direct_face_login'), data={'image': img_b64})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['username'], 'direct_face_user')
        self.assertEqual(data['redirect_url'], reverse('dashboard:index'))

        # Verify session is now authenticated
        dash_resp = self.client.get(reverse('dashboard:index'))
        self.assertEqual(dash_resp.status_code, 200)

    def test_login_page_renders_direct_face_auth_first_and_removes_badge(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        # Direct Face Auth option is prominent and rendered first
        self.assertContains(response, 'Direct Face Auth')
        self.assertContains(response, 'paneFaceAuth')
        self.assertContains(response, '/accounts/api/direct-face-login/')
        # Secondary static badge on Remember Me line is removed
        self.assertNotContains(response, 'bg-success-subtle text-success border border-success-subtle px-2 py-1 small fw-semibold')

    def test_unknown_face_rejected_with_message_and_options(self):
        # Scenario 2 & 3: Unknown Person Detection
        # Enrolls user A
        user = User.objects.create_user(username='enrolled_athlete', email='athlete@fitnova.com', password='password123')
        img_a = generate_test_face_image_base64(color=(130, 110, 100))
        session = self.client.session
        session['face_enroll_user_id'] = user.id
        session.save()
        self.client.post(reverse('accounts:api_face_enroll'), data={'image': img_a})
        self.client.logout()

        # Try to log in with a completely different person's face
        img_unknown = generate_different_face_image_base64()
        response = self.client.post(reverse('accounts:api_direct_face_login'), data={'image': img_unknown})
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertTrue(data['unknown_user'])
        self.assertTrue(data.get('is_new_user'))
        self.assertEqual(data['message'], "Face Not Recognized. Your account is not registered.")
        self.assertIn('login_url', data)
        self.assertIn('register_url', data)
        self.assertIn('redirect_url', data)

    def test_anti_spoofing_rejects_dark_image(self):
        # Scenario 4: Extreme darkness / invalid contrast
        dark_img = Image.new('RGB', (160, 160), color=(5, 5, 5))
        buf = BytesIO()
        dark_img.save(buf, format='JPEG')
        b64_dark = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')

        response = self.client.post(reverse('accounts:api_direct_face_login'), data={'image': b64_dark})
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])

    def test_duplicate_face_registration_blocked(self):
        # Scenario 6: Duplicate Face Registration Prevention
        user1 = User.objects.create_user(username='user_one', email='user1@fitnova.com', password='password123')
        img_b64 = generate_test_face_image_base64(color=(125, 105, 95))

        # User 1 enrolls face
        session1 = self.client.session
        session1['face_enroll_user_id'] = user1.id
        session1.save()
        resp1 = self.client.post(reverse('accounts:api_face_enroll'), data={'image': img_b64})
        self.assertEqual(resp1.status_code, 200)

        # Log out user1 before user2 attempts enrollment
        self.client.logout()

        # User 2 tries to register using the exact same face
        user2 = User.objects.create_user(username='user_two', email='user2@fitnova.com', password='password123')
        session2 = self.client.session
        session2['face_enroll_user_id'] = user2.id
        session2.save()
        resp2 = self.client.post(reverse('accounts:api_face_enroll'), data={'image': img_b64})
        self.assertEqual(resp2.status_code, 400)
        self.assertIn('Duplicate face registration is prohibited', resp2.json()['message'])

    def test_rate_limiting_lockout_after_repeated_failures(self):
        # Scenario 7: Rate Limiting & Account Lockout
        from apps.accounts.face_service import FaceAuthService
        test_ip = "192.168.1.99"
        FaceAuthService.reset_failed_attempts(test_ip, "biometric_live")

        for _ in range(10):
            FaceAuthService.record_failed_attempt(test_ip, "biometric_live")

        is_locked, lock_msg = FaceAuthService.check_rate_limit(test_ip, "biometric_live")
        self.assertTrue(is_locked)
        self.assertIn("locked", lock_msg)

    def test_postgresql_encrypted_template_persistence(self):
        # Scenario 9: PostgreSQL persistence & AES-256 Fernet encryption
        from apps.accounts.face_service import FaceAuthService
        user = User.objects.create_user(username='crypto_user', email='crypto@fitnova.com', password='password123')
        img_b64 = generate_test_face_image_base64()

        session = self.client.session
        session['face_enroll_user_id'] = user.id
        session.save()
        self.client.post(reverse('accounts:api_face_enroll'), data={'image': img_b64})

        prof = UserFaceProfile.objects.get(user=user)
        self.assertTrue(prof.encrypted_template)
        # Template should be encrypted (starts with Fernet gAAAAA prefix)
        self.assertTrue(prof.encrypted_template.startswith('gAAAAA'))
        decrypted = FaceAuthService.decrypt_biometric_data(prof.encrypted_template)
        self.assertEqual(decrypted['user_id'], user.id)
        self.assertEqual(len(decrypted['features']), 320)
