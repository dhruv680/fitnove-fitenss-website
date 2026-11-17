import re
import uuid
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import viewsets
from .models import User, GymOrganization, GymBranch, UserFaceProfile
from .face_service import FaceAuthService
from .serializers import UserSerializer, GymOrganizationSerializer, GymBranchSerializer
from .permissions import IsGymAdminUser, IsSuperAdminUser, admin_only

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

        # Set session flag and redirect to Login Page with success notification
        messages.success(request, f'Registration successful! Welcome to FitNova, {first_name}. You can now sign in with your credentials.')
        return redirect(reverse('accounts:login') + '?registered=1')

    return render(request, 'accounts/register.html')


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
    API endpoint: Securely saves facial feature vectors and descriptors.
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
    if not image_data:
        # Check json body
        try:
            data = json.loads(request.body.decode('utf-8'))
            image_data = data.get('image', '')
            raw_desc = data.get('descriptor', None)
        except Exception:
            raw_desc = None
    else:
        raw_desc = request.POST.get('descriptor', None)
        if raw_desc and isinstance(raw_desc, str):
            try:
                raw_desc = json.loads(raw_desc)
            except Exception:
                raw_desc = None

    if not image_data:
        return JsonResponse({'success': False, 'message': 'No face image provided.'}, status=400)

    success, message = FaceAuthService.enroll_user_face(target_user, image_data, descriptor=raw_desc)

    if success:
        # Clean up registration enrollment session
        request.session.pop('face_enroll_user_id', None)
        redirect_url = reverse('dashboard:index') if request.user.is_authenticated else (reverse('accounts:login') + '?registered=1')
        return JsonResponse({
            'success': True,
            'message': message,
            'redirect_url': redirect_url
        })
    else:
        return JsonResponse({'success': False, 'message': message}, status=400)


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
            messages.error(request, 'Invalid email or password. Please try again.')

    return render(request, 'accounts/login.html', {'registered_flag': registered_flag})


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

    matched, confidence, message = FaceAuthService.verify_user_face(pending_user, image_data, descriptor=raw_desc)

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
    return redirect('accounts:login')



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
        if user.is_super_admin:
            return GymBranch.objects.all()
        return GymBranch.objects.filter(organization=user.organization)

