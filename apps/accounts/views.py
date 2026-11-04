from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from rest_framework import viewsets
from .models import User, GymOrganization, GymBranch
from .serializers import UserSerializer, GymOrganizationSerializer, GymBranchSerializer
from .permissions import IsGymAdminUser, IsSuperAdminUser, admin_only

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

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

            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard:index')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')

    return render(request, 'accounts/login.html')


def logout_view(request):
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
