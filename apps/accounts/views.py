import re
import uuid
import json
import secrets
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.cache import never_cache
from .models import (
    User, GymOrganization, GymBranch, UserFaceProfile,
    FaceAuthenticationLog, FailedLoginAttempt, EmailVerificationOTP
)
from .face_service import FaceAuthService
from .serializers import UserSerializer, GymOrganizationSerializer, GymBranchSerializer
from .permissions import IsGymAdminUser, IsSuperAdminUser, admin_only

@ensure_csrf_cookie
@never_cache
def register_view(request):
    """
    Step 1: User Registration with complete field validation.
    Redirects to Step 2 (Face Registration) upon successful creation.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        username_input = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        role = request.POST.get('role', User.Role.MEMBER).strip().upper()
        valid_roles = [User.Role.MEMBER, User.Role.TRAINER, User.Role.STAFF, User.Role.GYM_ADMIN]
        if role not in valid_roles:
            role = User.Role.MEMBER
        gender = request.POST.get('gender', 'MALE').strip().upper()
        if gender not in [User.Gender.MALE, User.Gender.FEMALE, User.Gender.OTHER]:
            gender = User.Gender.MALE
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        terms = request.POST.get('terms')

        errors = []

        # Required fields validation
        if not full_name:
            errors.append('Full Name is required.')
        if not email:
            errors.append('Email address is required.')
        if not phone:
            errors.append('Mobile number is required.')
        if not password:
            errors.append('Password is required.')
        if not terms:
            errors.append('You must accept the Terms & Conditions.')

        # Username validation (if provided)
        if username_input:
            if not re.match(r'^[a-zA-Z0-9_.-]{3,30}$', username_input):
                errors.append('Username must be 3-30 characters long and contain only letters, numbers, dots, dashes, or underscores.')
            elif User.objects.filter(username__iexact=username_input).exists():
                errors.append('This username is already taken. Please choose another.')

        # Email format validation
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if email and not re.match(email_regex, email):
            errors.append('Please enter a valid email address.')

        # Duplicate email check
        if email and User.objects.filter(email__iexact=email).exists():
            errors.append('An account with this email address already exists. Please log in.')

        # Phone format validation (digits, optional leading +, 7-15 length)
        phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
        if phone and not re.match(r'^\+?[0-9]{7,15}$', phone_clean):
            errors.append('Please enter a valid mobile number (7-15 digits).')

        # Password validation
        if password:
            if len(password) < 8:
                errors.append('Password must be at least 8 characters long.')
            if password != confirm_password:
                errors.append('Passwords do not match.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'accounts/register.html', {
                'form_data': {
                    'full_name': full_name,
                    'username': username_input,
                    'email': email,
                    'phone': phone,
                    'role': role,
                    'gender': gender,
                }
            })

        # Name splitting
        name_parts = full_name.split(None, 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Final username
        if username_input:
            username = username_input
        else:
            base_username = slugify(full_name.replace(' ', '_')) or email.split('@')[0]
            username = base_username
            suffix = 1
            while User.objects.filter(username__iexact=username).exists():
                username = f"{base_username}_{suffix}"
                suffix += 1

        # Associate default organization & branch
        org = GymOrganization.objects.first()
        branch = org.branches.first() if org else None

        # Create User with hashed password
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            gender=gender,
            role=role,
            organization=org,
            branch=branch,
            is_active=True
        )

        # Create associated role profile
        if role == User.Role.MEMBER:
            try:
                from apps.members.models import Member
                member_id = f"FN-{timezone.now().year}-{user.id:04d}"
                Member.objects.create(
                    user=user,
                    organization=org,
                    branch=branch,
                    member_id=member_id,
                    status=Member.Status.ACTIVE,
                    qr_token=str(uuid.uuid4())
                )
            except Exception:
                pass
        elif role == User.Role.TRAINER:
            try:
                from apps.trainers.models import Trainer
                Trainer.objects.create(
                    user=user,
                    organization=org,
                    specialization='General Fitness & Personal Training',
                    status=Trainer.Status.ACTIVE
                )
            except Exception:
                pass

        # DIRECT FACE DETECTION AFTER REGISTRATION
        request.session['face_enroll_user_id'] = user.id
        messages.success(request, f'Account created for {first_name}! Starting automatic face detection...')
        return redirect('accounts:face_enroll')

    return render(request, 'accounts/register.html')


@ensure_csrf_cookie
@never_cache
def face_enroll_view(request):
    """
    Step 2: Face Registration Page.
    Opens the webcam and captures facial biometrics for future verification.
    """
    target_user = None
    if request.user.is_authenticated:
        target_user = request.user
    else:
        user_id = request.session.get('face_enroll_user_id')
        if user_id:
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                target_user = None

    if not target_user:
        messages.info(request, 'Please register or log in first.')
        return redirect('accounts:login')

    # Handle Skip / Fallback
    if request.method == 'POST' and request.POST.get('action') == 'skip':
        request.session.pop('face_enroll_user_id', None)
        if request.user.is_authenticated:
            messages.info(request, 'Face registration skipped. You can enroll anytime from your profile.')
            return redirect('dashboard:index')
        else:
            messages.success(request, 'Registration complete! You can now log in using your password.')
            return redirect('accounts:login')

    return render(request, 'accounts/face_enroll.html', {
        'target_user': target_user,
        'has_profile': target_user.has_face_enrolled,
    })


def api_face_enroll(request):
    """
    API endpoint: Securely saves AES-256 encrypted facial feature vectors and descriptors.
    Includes anti-duplicate registration protection and anti-spoofing check.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid HTTP method.'}, status=405)

    target_user = None
    if request.user.is_authenticated:
        target_user = request.user
    else:
        user_id = request.session.get('face_enroll_user_id')
        if user_id:
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                target_user = None

    if not target_user:
        return JsonResponse({'success': False, 'message': 'Authentication session expired. Please log in again.'}, status=401)

    image_data = request.POST.get('image', '').strip()
    raw_desc = request.POST.get('descriptor', None)
    samples_raw = request.POST.get('samples', None)

    if not image_data:
        try:
            data = json.loads(request.body.decode('utf-8'))
            image_data = data.get('image', '')
            raw_desc = data.get('descriptor', None)
            samples_raw = data.get('samples', None)
        except Exception:
            raw_desc = None

    if not image_data:
        return JsonResponse({'success': False, 'message': 'No face image provided.'}, status=400)

    if raw_desc and isinstance(raw_desc, str):
        try:
            raw_desc = json.loads(raw_desc)
        except Exception:
            raw_desc = None

    samples_list = None
    if samples_raw and isinstance(samples_raw, str):
        try:
            samples_list = json.loads(samples_raw)
        except Exception:
            samples_list = None

    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    success, message = FaceAuthService.enroll_user_face(
        target_user,
        image_data,
        descriptor=raw_desc,
        additional_samples=samples_list,
        ip_address=ip_address,
        user_agent=user_agent
    )

    if success:
        # Clean up registration enrollment session
        was_authenticated = request.user.is_authenticated
        request.session.pop('face_enroll_user_id', None)

        if was_authenticated:
            # User was already logged in (e.g. updating biometrics from profile)
            redirect_url = reverse('dashboard:index')
            msg = 'Face Biometrics Enrolled & Encrypted! Welcome to FitNova.'
        else:
            # Registration complete: redirect user to Login Page so they authenticate with their face to enter
            redirect_url = reverse('accounts:login') + '?registered=1'
            msg = 'Face registered successfully! Please look at the camera to log in with Face ID.'

        return JsonResponse({
            'success': True,
            'message': msg,
            'redirect_url': redirect_url
        })
    else:
        is_dup = 'already' in message.lower() or 'duplicate' in message.lower()
        return JsonResponse({
            'success': False,
            'is_duplicate': is_dup,
            'message': message,
            'login_url': reverse('accounts:login')
        }, status=400)


@ensure_csrf_cookie
@never_cache
def login_view(request):
    """
    Login view supporting Email/Username + Password.
    If user has Face Biometrics enrolled, redirects to Face Verification step.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    # If already pending face verification, redirect there directly
    if request.session.get('face_auth_pending_user_id'):
        return redirect('accounts:face_verify')

    registered_flag = request.GET.get('registered') == '1'

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = bool(request.POST.get('remember_me'))

        if not username or not password:
            messages.error(request, 'Please provide both username/email and password.')
            return render(request, 'accounts/login.html')

        user = authenticate(request, username=username, password=password)
        if not user and '@' in username:
            try:
                user_obj = User.objects.get(email__iexact=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                user = None

        if user is not None:
            if not user.is_active:
                messages.error(request, 'This account is deactivated. Please contact your administrator.')
                return render(request, 'accounts/login.html')

            # Check if user has Face Biometrics enrolled
            if user.has_face_enrolled:
                # Set intermediate session state for Face Verification
                request.session['face_auth_pending_user_id'] = user.id
                request.session['face_auth_remember_me'] = remember_me
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    request.session['face_auth_next_url'] = next_url
                return redirect('accounts:face_verify')
            else:
                # Direct login if face is not enrolled yet
                login(request, user)
                if remember_me:
                    request.session.set_expiry(1209600)  # 2 weeks
                else:
                    request.session.set_expiry(0)       # browser session
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard:index')
        else:
            # If account does not exist in the system, redirect to Registration Page
            account_exists = User.objects.filter(
                Q(username__iexact=username) | Q(email__iexact=username)
            ).exists()
            if not account_exists:
                messages.info(request, 'Your account is not registered. Please create a new account.')
                return redirect('accounts:register')
            messages.error(request, 'Invalid email or password. Please try again.')

    return render(request, 'accounts/login.html', {'registered_flag': registered_flag})


def api_direct_face_login(request):
    """
    Direct Face Authentication API (Option 1):
    Instant 1-to-N face recognition login without requiring manual password entry.
    Takes live camera image and matches against registered biometric profiles.
    - Liveness verification & anti-spoofing
    - Rate-limiting & lockout
    - On unknown face: returns 'Face Not Recognized. Your account is not registered.' with action options.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid HTTP method.'}, status=405)

    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    # Rate limiting & lockout check
    is_locked, lock_msg = FaceAuthService.check_rate_limit(ip_address, "biometric_live")
    if is_locked:
        return JsonResponse({
            'success': False,
            'locked': True,
            'message': lock_msg
        }, status=429)

    image_data = request.POST.get('image', '').strip()
    raw_desc = request.POST.get('descriptor', None)

    if not image_data:
        try:
            data = json.loads(request.body.decode('utf-8'))
            image_data = data.get('image', '')
            raw_desc = data.get('descriptor', None)
        except Exception:
            raw_desc = None

    if not image_data:
        return JsonResponse({'success': False, 'message': 'No face image captured.'}, status=400)

    if raw_desc and isinstance(raw_desc, str):
        try:
            raw_desc = json.loads(raw_desc)
        except Exception:
            raw_desc = None

    identifier = request.POST.get('identifier', '').strip()
    if not identifier:
        try:
            data = json.loads(request.body.decode('utf-8'))
            identifier = data.get('identifier', '').strip()
        except Exception:
            identifier = ''

    if identifier:
        from django.db.models import Q
        target_account = User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()
        if not target_account:
            return JsonResponse({
                'success': False,
                'unknown_user': True,
                'message': 'Account not registered. Please create a new account or check your username/email.',
                'register_url': reverse('accounts:register')
            }, status=401)

        matched, confidence, message = FaceAuthService.verify_user_face(
            target_account,
            image_data,
            descriptor=raw_desc,
            ip_address=ip_address,
            user_agent=user_agent
        )
        if matched:
            matched_user = target_account
        else:
            return JsonResponse({
                'success': False,
                'message': message or 'Face verification failed for this account.',
                'confidence': confidence
            }, status=401)
    else:
        matched_user, confidence, message = FaceAuthService.identify_user_face(
            image_data,
            descriptor=raw_desc,
            ip_address=ip_address,
            user_agent=user_agent
        )

    if matched_user:
        login(request, matched_user, backend='django.contrib.auth.backends.ModelBackend')
        request.session.set_expiry(1209600)  # 2 weeks session persistence
        request.session['face_authenticated'] = True

        # Clear any pending states
        request.session.pop('face_auth_pending_user_id', None)

        next_url = request.POST.get('next') or request.GET.get('next') or reverse('dashboard:index')
        user_name = matched_user.get_full_name() or matched_user.username

        return JsonResponse({
            'success': True,
            'message': f"Face Authenticated! Welcome, {user_name}!",
            'user': user_name,
            'username': matched_user.username,
            'role': matched_user.get_role_display(),
            'confidence': confidence,
            'redirect_url': next_url
        })
    else:
        # Unknown Person / New User: Redirect to Registration Form
        register_url = reverse('accounts:register') + '?new_user=1'
        return JsonResponse({
            'success': False,
            'unknown_user': True,
            'is_new_user': True,
            'message': message or 'Face Not Recognized. Your account is not registered.',
            'confidence': confidence,
            'login_url': reverse('accounts:login'),
            'register_url': register_url,
            'redirect_url': register_url
        }, status=401)


@ensure_csrf_cookie
@never_cache
def face_verify_view(request):
    """
    Step 2 of Login: Automatic Biometric Face Verification page.
    Webcam continuously scans and verifies the user before granting dashboard access.
    """
    pending_user_id = request.session.get('face_auth_pending_user_id')
    if not pending_user_id:
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        return redirect('accounts:login')

    pending_user = get_object_or_404(User, id=pending_user_id)
    return render(request, 'accounts/face_verify.html', {
        'pending_user': pending_user
    })


def api_face_verify(request):
    """
    API endpoint: Verifies captured camera face against pending user's enrolled biometric template.
    On match, calls login(request, pending_user) and returns redirect to dashboard.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid HTTP method.'}, status=405)

    pending_user_id = request.session.get('face_auth_pending_user_id')
    if not pending_user_id:
        return JsonResponse({'success': False, 'message': 'No pending login session found.'}, status=401)

    try:
        pending_user = User.objects.get(id=pending_user_id)
    except User.DoesNotExist:
        request.session.pop('face_auth_pending_user_id', None)
        return JsonResponse({'success': False, 'message': 'User account not found.'}, status=404)

    image_data = request.POST.get('image', '').strip()
    raw_desc = request.POST.get('descriptor', None)
    if not image_data:
        try:
            data = json.loads(request.body.decode('utf-8'))
            image_data = data.get('image', '')
            raw_desc = data.get('descriptor', None)
        except Exception:
            raw_desc = None

    if not image_data:
        return JsonResponse({'success': False, 'message': 'No face image provided.'}, status=400)

    if raw_desc and isinstance(raw_desc, str):
        try:
            raw_desc = json.loads(raw_desc)
        except Exception:
            raw_desc = None

    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    matched, confidence, message = FaceAuthService.verify_user_face(
        pending_user,
        image_data,
        descriptor=raw_desc,
        ip_address=ip_address,
        user_agent=user_agent
    )

    if matched:
        # Complete full Django authentication
        login(request, pending_user, backend='django.contrib.auth.backends.ModelBackend')
        remember_me = request.session.pop('face_auth_remember_me', False)
        if remember_me:
            request.session.set_expiry(1209600)  # 2 weeks
        else:
            request.session.set_expiry(0)       # browser session

        next_url = request.session.pop('face_auth_next_url', None) or reverse('dashboard:index')
        request.session.pop('face_auth_pending_user_id', None)
        request.session['face_authenticated'] = True

        return JsonResponse({
            'success': True,
            'message': f'Face Verified! Welcome back, {pending_user.first_name or pending_user.username}.',
            'confidence': confidence,
            'redirect_url': next_url
        })
    else:
        return JsonResponse({
            'success': False,
            'message': message,
            'confidence': confidence
        }, status=401)


def face_fallback_view(request):
    """
    Alternative verification fallback: In case webcam is unavailable,
    allows confirming identity with password to access dashboard.
    """
    pending_user_id = request.session.get('face_auth_pending_user_id')
    if not pending_user_id:
        return redirect('accounts:login')

    pending_user = get_object_or_404(User, id=pending_user_id)

    if request.method == 'POST':
        password = request.POST.get('password', '')
        if pending_user.check_password(password):
            login(request, pending_user, backend='django.contrib.auth.backends.ModelBackend')
            request.session.pop('face_auth_pending_user_id', None)
            request.session['face_authenticated'] = True
            messages.success(request, f'Welcome back, {pending_user.first_name or pending_user.username}!')
            return redirect('dashboard:index')
        else:
            messages.error(request, 'Incorrect password. Please try again.')

    return render(request, 'accounts/face_fallback.html', {'pending_user': pending_user})


def logout_view(request):
    # Clear any pending face session
    request.session.pop('face_auth_pending_user_id', None)
    request.session.pop('face_enroll_user_id', None)
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('accounts:register')


@login_required
@never_cache
def api_remove_face(request):
    """
    User Privacy & Control: Securely purges user's biometric face template.
    Allows re-enrollment or pure password authentication.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid HTTP method.'}, status=405)

    user = request.user
    if hasattr(user, 'face_auth_profile'):
        profile = user.face_auth_profile
        # Secure biometric deletion: clean image file if present
        if profile.face_image:
            try:
                profile.face_image.delete(save=False)
            except Exception:
                pass
        profile.delete()

        FaceAuthService.log_security_event(
            FaceAuthenticationLog.EventType.SUCCESS,
            status='DELETED',
            user=user,
            reason="Biometric face profile securely purged by user."
        )
        messages.success(request, 'Your biometric face profile has been permanently and securely deleted.')
        return JsonResponse({'success': True, 'message': 'Biometric profile securely removed.'})
    else:
        return JsonResponse({'success': False, 'message': 'No face biometric profile found.'}, status=404)



@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name).strip()
        user.last_name = request.POST.get('last_name', user.last_name).strip()
        user.email = request.POST.get('email', user.email).strip()
        user.phone = request.POST.get('phone', user.phone).strip()
        user.address = request.POST.get('address', user.address).strip()

        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']

        user.save()
        messages.success(request, 'Your profile details have been updated.')
        return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {'profile_user': user})


@login_required
def change_password_view(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(current_password):
            messages.error(request, 'Your current password is incorrect.')
            return redirect('accounts:profile')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('accounts:profile')

        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('accounts:profile')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Your password was successfully updated!')
        return redirect('accounts:profile')

    return redirect('accounts:profile')


# REST API Viewsets
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsGymAdminUser]

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return User.objects.all()
        return User.objects.filter(organization=user.organization)


class GymOrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = GymOrganizationSerializer
    permission_classes = [IsSuperAdminUser]
    queryset = GymOrganization.objects.all()


class GymBranchViewSet(viewsets.ModelViewSet):
    serializer_class = GymBranchSerializer
    permission_classes = [IsGymAdminUser]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return GymBranch.objects.none()
        if user.is_super_admin:
            return GymBranch.objects.all()
        if user.organization:
            return GymBranch.objects.filter(organization=user.organization)
        org = GymOrganization.objects.first()
        if org:
            return GymBranch.objects.filter(organization=org)
        return GymBranch.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        org = getattr(user, 'organization', None) or GymOrganization.objects.first()
        serializer.save(organization=org)


def api_send_email_otp(request):
    """
    High-Security Email OTP Verification Dispatcher.
    Generates cryptographically random 6-digit code and logs security event.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid HTTP method.'}, status=405)

    email = request.POST.get('email', '').strip().lower()
    if not email or '@' not in email:
        return JsonResponse({'success': False, 'message': 'Please provide a valid email address.'}, status=400)

    # Check if duplicate email already exists
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({'success': False, 'message': 'An account with this email already exists. Please sign in.'}, status=400)

    code = f"{secrets.randbelow(900000) + 100000}"
    expires = timezone.now() + timedelta(minutes=10)

    EmailVerificationOTP.objects.filter(email__iexact=email).delete()
    EmailVerificationOTP.objects.create(email=email, otp_code=code, expires_at=expires)

    try:
        send_mail(
            subject="FitNova Security: Your Account Verification Code",
            message=f"Hello,\n\nYour 6-digit FitNova registration code is: {code}\n\nThis code will expire in 10 minutes.\n\nStay fit,\nThe FitNova Security Team",
            from_email="security@fitnova.com",
            recipient_list=[email],
            fail_silently=True
        )
    except Exception:
        pass

    return JsonResponse({
        'success': True,
        'message': f"6-digit verification code sent to {email}.",
        'dev_code': code if getattr(settings, 'DEBUG', False) else None
    })


def api_verify_email_otp(request):
    """Validates submitted 6-digit email OTP."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid HTTP method.'}, status=405)

    email = request.POST.get('email', '').strip().lower()
    otp = request.POST.get('otp', '').strip()

    if not email or not otp:
        return JsonResponse({'success': False, 'message': 'Email and verification code are required.'}, status=400)

    record = EmailVerificationOTP.objects.filter(email__iexact=email, otp_code=otp).first()
    if not record:
        return JsonResponse({'success': False, 'message': 'Incorrect verification code. Please check your inbox.'}, status=400)

    if record.expires_at < timezone.now():
        return JsonResponse({'success': False, 'message': 'Verification code has expired. Please request a new code.'}, status=400)

    record.is_verified = True
    record.save(update_fields=['is_verified'])

    return JsonResponse({
        'success': True,
        'message': 'Email verified successfully! You can now proceed to Face Registration.'
    })

