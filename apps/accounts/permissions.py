from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from rest_framework import permissions

def role_required(*allowed_roles):
    """
    Decorator for views that checks whether the logged-in user has one of the allowed roles.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.is_superuser or request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have permission to access that section.")
            return redirect('dashboard:index')
        return _wrapped_view
    return decorator


def admin_only(view_func):
    return role_required('SUPER_ADMIN', 'GYM_ADMIN')(view_func)


def staff_or_admin(view_func):
    return role_required('SUPER_ADMIN', 'GYM_ADMIN', 'STAFF')(view_func)


def trainer_or_above(view_func):
    return role_required('SUPER_ADMIN', 'GYM_ADMIN', 'STAFF', 'TRAINER')(view_func)


# DRF Permissions
class IsSuperAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_super_admin)


class IsGymAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_gym_admin)


class IsStaffOrAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff_member)


class IsOrganizationMember(permissions.BasePermission):
    """
    Ensures that object-level access is scoped to the requesting user's organization.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        # If object has organization attribute
        if hasattr(obj, 'organization'):
            return obj.organization == request.user.organization
        # If object is a member profile or linked via member
        if hasattr(obj, 'member') and hasattr(obj.member, 'organization'):
            return obj.member.organization == request.user.organization
        return True

