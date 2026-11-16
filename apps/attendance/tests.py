from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User, GymOrganization, GymBranch
from apps.members.models import Member
from apps.memberships.models import MembershipPlan, Membership
from apps.attendance.models import Attendance
from apps.attendance.services import AttendanceService

class AttendanceServiceTestCase(TestCase):
    def setUp(self):
        self.org = GymOrganization.objects.create(name='Test Gym', slug='test-gym', phone='1234567890')
        self.branch = GymBranch.objects.create(organization=self.org, name='Main Branch', code='TB-01', phone='1234567890')
        self.user = User.objects.create_user(username='testmember', password='password123', organization=self.org, branch=self.branch, role=User.Role.MEMBER)
        self.member = Member.objects.create(
            user=self.user,
            organization=self.org,
            branch=self.branch,
            member_id='FN-TEST-001',
            status=Member.Status.ACTIVE
        )
        self.plan = MembershipPlan.objects.create(organization=self.org, name='Gold Plan', slug='gold', price=100.00, duration_days=30)
        self.membership = Membership.objects.create(
            member=self.member,
            plan=self.plan,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            status=Membership.Status.ACTIVE
        )

    def test_check_in_success(self):
        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"
        success, msg, att, action = AttendanceService.process_check_in(qr_payload)
        self.assertTrue(success)
        self.assertEqual(action, 'CHECK_IN')
        self.assertEqual(att.status, Attendance.Status.PRESENT)
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 1)

    def test_duplicate_prevention(self):
        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"
        # 1st scan = check in
        success1, msg1, att1, action1 = AttendanceService.process_check_in(qr_payload)
        self.assertTrue(success1)
        self.assertEqual(action1, 'CHECK_IN')

        # 2nd scan on same day = duplicate blocked!
        success2, msg2, att2, action2 = AttendanceService.process_check_in(qr_payload)
        self.assertFalse(success2)
        self.assertEqual(action2, 'DUPLICATE')
        self.assertIn('Already Checked In', msg2)
        # Verify still exactly 1 record in database
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 1)

    def test_test_mode_no_database_record(self):
        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"
        success, msg, att, action = AttendanceService.process_check_in(qr_payload, is_test=True)
        self.assertTrue(success)
        self.assertEqual(action, 'TEST_SUCCESS')
        # Verify no attendance was created in DB
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 0)

    def test_verify_member_ready_check_in(self):
        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"
        can_confirm, msg, member, action, existing = AttendanceService.verify_member_for_attendance(qr_payload)
        self.assertTrue(can_confirm)
        self.assertEqual(action, 'READY_CHECK_IN')
        self.assertEqual(member.id, self.member.id)
        # Verify no attendance was written to DB!
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 0)

    def test_verify_member_expired(self):
        self.membership.end_date = timezone.now().date() - timezone.timedelta(days=2)
        self.membership.status = Membership.Status.EXPIRED
        self.membership.save()

        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"
        can_confirm, msg, member, action, existing = AttendanceService.verify_member_for_attendance(qr_payload)
        self.assertFalse(can_confirm)
        self.assertEqual(action, 'EXPIRED')
        self.assertIn('Membership expired', msg)

    def test_verify_member_inactive(self):
        self.member.status = Member.Status.INACTIVE
        self.member.save()

        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"
        can_confirm, msg, member, action, existing = AttendanceService.verify_member_for_attendance(qr_payload)
        self.assertFalse(can_confirm)
        self.assertEqual(action, 'INACTIVE')
        self.assertIn('INACTIVE', msg)

    def test_verify_member_forged_token(self):
        qr_payload = f"FITNOVA:{self.member.member_id}:invalid-token-12345"
        can_confirm, msg, member, action, existing = AttendanceService.verify_member_for_attendance(qr_payload)
        self.assertFalse(can_confirm)
        self.assertEqual(action, 'INVALID_QR')

    def test_api_verify_and_confirm_workflow(self):
        # Authenticate staff user
        staff_user = User.objects.create_user(
            username='staffadmin',
            password='password123',
            organization=self.org,
            branch=self.branch,
            role=User.Role.STAFF
        )
        self.client.login(username='staffadmin', password='password123')

        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"

        # Step 1: Verify API
        response = self.client.post('/attendance/api/verify/', {'identifier': qr_payload})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'READY_CHECK_IN')
        self.assertEqual(data['member']['member_id'], self.member.member_id)
        # Ensure no attendance record yet
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 0)

        # Step 2: Confirm API
        response = self.client.post('/attendance/api/confirm/', {'identifier': qr_payload})
        self.assertEqual(response.status_code, 200)
        confirm_data = response.json()
        self.assertTrue(confirm_data['success'])
        self.assertEqual(confirm_data['action'], 'CHECK_IN')
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 1)

    def test_api_scan_direct_and_duplicate(self):
        staff_user = User.objects.create_user(
            username='staffdirect',
            password='password123',
            organization=self.org,
            branch=self.branch,
            role=User.Role.STAFF
        )
        self.client.login(username='staffdirect', password='password123')
        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"

        # 1. Direct Scan API
        response = self.client.post('/attendance/api/scan/', {'identifier': qr_payload})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'CHECK_IN')
        self.assertEqual(data['member']['name'], self.member.full_name)
        self.assertIsNotNone(data['member']['check_in_time'])
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 1)

        # 2. Duplicate Scan via API
        dup_response = self.client.post('/attendance/api/scan/', {'identifier': qr_payload})
        self.assertEqual(dup_response.status_code, 200)
        dup_data = dup_response.json()
        self.assertFalse(dup_data['success'])
        self.assertEqual(dup_data['action'], 'DUPLICATE')
        self.assertIn('Already Checked In', dup_data['message'])
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 1)

    def test_api_scan_test_mode(self):
        staff_user = User.objects.create_user(
            username='stafftester',
            password='password123',
            organization=self.org,
            branch=self.branch,
            role=User.Role.STAFF
        )
        self.client.login(username='stafftester', password='password123')
        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"

        response = self.client.post('/attendance/api/scan/', {'identifier': qr_payload, 'is_test': 'true'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'TEST_SUCCESS')
        self.assertTrue(data['is_test'])
        # Ensure zero records created in DB
        self.assertEqual(Attendance.objects.filter(member=self.member).count(), 0)

    def test_api_scan_accepts_json_payload(self):
        staff_user = User.objects.create_user(
            username='staffjson',
            password='password123',
            organization=self.org,
            branch=self.branch,
            role=User.Role.STAFF
        )
        self.client.login(username='staffjson', password='password123')
        qr_payload = f"FITNOVA:{self.member.member_id}:{self.member.qr_token}"

        response = self.client.post(
            '/attendance/api/scan/',
            data='{"identifier": "%s"}' % qr_payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['member']['name'], self.member.full_name)


class FaceRecognitionTestCase(TestCase):
    def setUp(self):
        self.org = GymOrganization.objects.create(name='Face Gym', slug='face-gym', phone='1234567890')
        self.branch = GymBranch.objects.create(organization=self.org, name='Face Branch', code='FB-01', phone='1234567890')
        self.staff_user = User.objects.create_user(
            username='facestaff', password='password123',
            organization=self.org, branch=self.branch, role=User.Role.STAFF
        )
        self.member_user = User.objects.create_user(
            username='facemember', password='password123',
            first_name='Alex', last_name='Morgan',
            organization=self.org, branch=self.branch, role=User.Role.MEMBER
        )
        self.member = Member.objects.create(
            user=self.member_user, organization=self.org, branch=self.branch,
            member_id='FN-FACE-001', status=Member.Status.ACTIVE
        )
        self.plan = MembershipPlan.objects.create(organization=self.org, name='Elite Plan', slug='elite', price=150.00, duration_days=30)
        self.membership = Membership.objects.create(
            member=self.member, plan=self.plan,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            status=Membership.Status.ACTIVE
        )

        # Create a sample base64 test face image (64x64 solid square with gradient)
        import io, base64
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (100, 100), color=(180, 140, 110))
        d = ImageDraw.Draw(img)
        d.ellipse([25, 25, 75, 75], fill=(220, 180, 150))
        d.rectangle([35, 40, 45, 45], fill=(40, 40, 40)) # eye 1
        d.rectangle([55, 40, 65, 45], fill=(40, 40, 40)) # eye 2
        d.line([40, 65, 60, 65], fill=(160, 50, 50), width=3) # mouth
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        self.sample_face_b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')

        # Dummy neural descriptor (128 floats)
        self.sample_descriptor = [0.05 * (i % 7) for i in range(128)]

    def test_face_enrollment_service(self):
        from apps.attendance.face_service import FaceRecognitionService
        success, msg = FaceRecognitionService.enroll_member_face(
            self.member, self.sample_face_b64, descriptor=self.sample_descriptor
        )
        self.assertTrue(success)
        self.assertIn("enrolled successfully", msg)
        self.assertTrue(hasattr(self.member, 'face_profile'))
        self.assertTrue(self.member.face_profile.is_active)

    def test_face_verification_api_success(self):
        from apps.attendance.face_service import FaceRecognitionService
        # Enroll first
        FaceRecognitionService.enroll_member_face(
            self.member, self.sample_face_b64, descriptor=self.sample_descriptor
        )

        self.client.login(username='facestaff', password='password123')
        import json
        response = self.client.post('/attendance/api/face-verify/', {
            'face_image': self.sample_face_b64,
            'face_descriptor': json.dumps(self.sample_descriptor)
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'FACE_VERIFIED')
        self.assertEqual(data['member']['name'], 'Alex Morgan')
        self.assertEqual(data['redirect_url'], '/')

        # Verify attendance record was saved in database
        att = Attendance.objects.filter(member=self.member, date=timezone.localdate()).first()
        self.assertIsNotNone(att)
        self.assertEqual(att.method, Attendance.CheckInMethod.FACE_RECOGNITION)
        self.assertEqual(att.status, Attendance.Status.PRESENT)

    def test_face_verification_duplicate_prevention(self):
        from apps.attendance.face_service import FaceRecognitionService
        FaceRecognitionService.enroll_member_face(
            self.member, self.sample_face_b64, descriptor=self.sample_descriptor
        )

        self.client.login(username='facestaff', password='password123')
        import json
        # 1st verification = success
        res1 = self.client.post('/attendance/api/face-verify/', {
            'face_image': self.sample_face_b64,
            'face_descriptor': json.dumps(self.sample_descriptor)
        })
        self.assertTrue(res1.json()['success'])

        # 2nd verification = duplicate blocked!
        res2 = self.client.post('/attendance/api/face-verify/', {
            'face_image': self.sample_face_b64,
            'face_descriptor': json.dumps(self.sample_descriptor)
        })
        data2 = res2.json()
        self.assertFalse(data2['success'])
        self.assertEqual(data2['action'], 'DUPLICATE')
        self.assertIn('Already Checked In', data2['message'])

    def test_face_verification_unregistered_rejected(self):
        self.client.login(username='facestaff', password='password123')
        import json
        unregistered_descriptor = [-0.9 for _ in range(128)]
        response = self.client.post('/attendance/api/face-verify/', {
            'face_image': self.sample_face_b64,
            'face_descriptor': json.dumps(unregistered_descriptor)
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['action'], 'UNREGISTERED')
        self.assertIn('Unregistered Face', data['message'])




